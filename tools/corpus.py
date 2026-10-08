"""Local replay evidence index. Collection MMR is accepted, never re-screened."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COHORT = '2500+ at collection, accepted from user; no MMR revalidation'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Source asset must remain inside the supplied root')
    return path


def index_record(source, record):
    # MMR metadata is deliberately neither read nor used as an eligibility gate.
    keys = ('sha256', 'path', 'matchup', 'map', 'mapSha1', 'split', 'frames',
            'cache', 'stateStatus', 'externallyCorroborated', 'unresolvedTags')
    result = {k: record.get(k) for k in keys}
    result['perspectives'] = [
        {k: p.get(k) for k in ('owner', 'classification', 'startDepots', 'opening', 'buildSequence')}
        for p in record.get('perspectives', [])]
    problems = []
    replay = inside(source, record['path'])
    if not replay.is_file():
        problems.append('replay_missing')
    elif digest(replay) != record['sha256']:
        problems.append('replay_hash_mismatch')
    if record.get('split') not in ('analysis', 'holdout'):
        problems.append('unknown_split')
    if record.get('stateStatus') != 'zero_generation_mismatch':
        problems.append(record.get('stateStatus', 'state_status_missing'))
    cache = record.get('cache')
    if cache:
        try:
            with gzip.open(inside(source, cache), 'rt', encoding='utf-8') as f:
                states = json.load(f)
            if states.get('sourceReplaySha256') != record['sha256']:
                problems.append('state_source_hash_mismatch')
            if states.get('mismatchedTags') != 0:
                problems.append('state_generation_mismatch')
        except (OSError, ValueError, EOFError):
            problems.append('state_cache_unreadable')
    else:
        problems.append('state_cache_missing')
    result['technicalIssues'] = sorted(set(problems))
    result['stateEligible'] = not problems
    # Existing independent comparison only covers the opening's first 8 minutes.
    result['corroboratedThroughFrame'] = 11520 if record.get('externallyCorroborated') else 0
    return result


def import_corpus(source, output):
    source, output = source.resolve(), output.resolve()
    census_path = source / 'reports/opening-census.json'
    census = read_json(census_path)
    records = [index_record(source, r) for r in census['records']]
    splits = {}
    for r in records:
        previous = splits.setdefault(r['sha256'], r['split'])
        if previous != r['split']:
            raise ValueError('Same replay occurs in both analysis and holdout')
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'corpus.jsonl').open('w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    map_index = read_json(source / 'build/maps/index.json')
    maps = []
    for name, m in sorted(map_index.items()):
        asset = inside(source, 'build/maps/' + m['file'])
        sha = digest(asset)
        if sha not in m['variants']:
            raise ValueError('Map CHK digest differs from census: ' + name)
        hashes = sorted({r['mapSha1'] for r in records if r['map'] == name})
        maps.append(dict(name=name, file=str(asset), chkSha256=sha, bwapiMapHashes=hashes))
    summary = dict(schemaVersion=1, cohort=COHORT, mmrExcluded=0,
                   sourceCensusSha256=digest(census_path),
                   totalReplays=len(records), uniqueReplays=len(splits),
                   byMatchup=dict(Counter(r['matchup'] for r in records)),
                   bySplit=dict(Counter(r['split'] for r in records)),
                   stateEligible=sum(r['stateEligible'] for r in records),
                   corroboratedOpeningReplays=sum(r['stateEligible'] and bool(r['corroboratedThroughFrame']) for r in records),
                   technicalIssues=dict(Counter(i for r in records for i in r['technicalIssues'])),
                   stateLimit='Zero generation mismatch alone does not establish simulation fidelity.')
    for name, data in [('summary.json', summary), ('maps.json', maps),
                       ('local.json', {'sourceRoot': str(source)})]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def candidates(records, map_hash, matchup, opening, frame, provisional=False):
    for record in records:
        if (record['mapSha1'] != map_hash or record['matchup'] != matchup
                or record['split'] != 'analysis' or not record['stateEligible']):
            continue
        if not provisional and frame > record['corroboratedThroughFrame']:
            continue
        for perspective in record['perspectives']:
            if perspective['classification'] == opening:
                yield record, perspective


def state_at(snaps, owner, frame):
    # Never use a later observation to represent what the player knew now.
    rows = [s for s in snaps if s[1] == owner and s[0] <= frame]
    if not rows:
        return None
    row = max(rows, key=lambda s: s[0])
    return row if frame - row[0] <= 48 else None


def features(row):
    return dict(frame=row[0], minerals=row[2], gas=row[3], supply=row[4] / 2,
                supplyMax=row[5] / 2, workers=row[6], armyValue=row[7],
                armyUnits=row[8], enemyVisibleValue=row[13], enemyKnownValue=row[14],
                enemyNearHomeValue=row[15], bases=row[16], basesBuilding=row[17],
                units=row[18], depots=row[19], armyCells=row[20],
                staticDefences=row[21], seenEnemyCells=row[22], upgrades=row[23])


# Explicit scaling only; this is case retrieval, not a learned policy or win probability.
SCALES = {'workers': 10, 'armyValue': 1000, 'bases': 1, 'minerals': 400,
          'gas': 200, 'enemyNearHomeValue': 500}


def find_cases(data, map_hash, matchup, opening, frame, target=None, start=None,
               provisional=False, limit=5):
    source = Path(read_json(data / 'local.json')['sourceRoot'])
    records = [json.loads(s) for s in (data / 'corpus.jsonl').read_text(encoding='utf-8').splitlines()]
    found = []
    for record, perspective in candidates(records, map_hash, matchup, opening, frame, provisional):
        with gzip.open(inside(source, record['cache']), 'rt', encoding='utf-8') as f:
            states = json.load(f)
        if states.get('sourceReplaySha256') != record['sha256']:
            raise ValueError('State cache changed; reimport before use')
        row = state_at(states['snaps'], perspective['owner'], frame)
        if row is None:
            continue
        situation = features(row)
        score = sum(abs(situation[k] - v) / SCALES[k] for k, v in (target or {}).items())
        if start:
            if not perspective['startDepots']:
                continue
            xy = perspective['startDepots'][0][:2]
            if list(start) != xy:
                continue
        found.append(dict(replaySha256=record['sha256'], owner=perspective['owner'],
                          replay=str(inside(source, record['path'])), mapHash=map_hash,
                          opening=opening, startDepots=perspective['startDepots'],
                          distance=score, situation=situation,
                          evidence='corroborated opening' if frame <= record['corroboratedThroughFrame'] else 'provisional states',
                          nextBuildObservations=[b for b in perspective['buildSequence']
                                                 if frame < b['frame'] <= min(frame + 1440,
                                                     record['corroboratedThroughFrame'] if not provisional else frame + 1440)]))
    return sorted(found, key=lambda r: (r['distance'], r['replaySha256'], r['owner']))[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    imp = subs.add_parser('import')
    imp.add_argument('--source-root', type=Path, required=True)
    imp.add_argument('--output', type=Path, default=ROOT / 'data')
    query = subs.add_parser('find')
    query.add_argument('--data', type=Path, default=ROOT / 'data')
    query.add_argument('--map-hash', required=True)
    query.add_argument('--matchup', choices=['pvp', 'pvt', 'pvz'], required=True)
    query.add_argument('--opening', required=True)
    query.add_argument('--frame', type=int, required=True)
    query.add_argument('--start', type=int, nargs=2)
    query.add_argument('--provisional', action='store_true')
    query.add_argument('--limit', type=int, default=5)
    for name in SCALES:
        query.add_argument('--' + name, type=float)
    args = parser.parse_args()
    if args.command == 'import':
        result = import_corpus(args.source_root, args.output)
    else:
        if args.frame < 0 or args.limit < 1:
            parser.error('Frame must be non-negative and limit positive')
        target = {k: getattr(args, k) for k in SCALES if getattr(args, k) is not None}
        result = find_cases(args.data, args.map_hash, args.matchup, args.opening, args.frame,
                            target, args.start, args.provisional, args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
