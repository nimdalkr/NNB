"""Check local map assets and BWTA cache prerequisites without touching a game."""
import argparse
import json
from pathlib import Path
from corpus import ROOT, digest, read_json


def inspect(maps, runtime):
    results = []
    for item in maps:
        issues = []
        chk = Path(item['file'])
        if not chk.is_file() or digest(chk) != item['chkSha256']:
            issues.append('CHK missing or changed')
        if not item['bwapiMapHashes']:
            issues.append('No observed map hash')
        for map_hash in item['bwapiMapHashes']:
            cache = runtime / 'bwapi-data/BWTA2' / (map_hash + '.bwta')
            if not cache.is_file():
                issues.append('Missing BWTA cache: ' + cache.name)
            else:
                with cache.open('r', encoding='ascii', errors='replace') as f:
                    header = f.readline(64).split()
                if not header or header[0] != '6':
                    issues.append('BWTA cache version must be 6')
        results.append({'map': item['name'], 'issues': issues})
    return dict(prerequisitesPresent=not any(r['issues'] for r in results),
                gameplayValidated=False, maps=results,
                limitation='Presence/version check only. Cache geometry, bases and paths need native validation.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--maps', type=Path, default=ROOT / 'data/maps.json')
    p.add_argument('--runtime', type=Path, required=True)
    a = p.parse_args()
    result = inspect(read_json(a.maps), a.runtime)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result['prerequisitesPresent'] else 2)
