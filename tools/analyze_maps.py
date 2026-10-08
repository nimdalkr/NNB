"""Generate exact-map BWTA inputs from the local CHK and extracted game tilesets."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import datetime
from corpus import ROOT, digest, read_json

TILESETS = ['badlands', 'platform', 'install', 'ashworld', 'jungle', 'desert', 'ice', 'twilight']


def chunks(raw):
    at, result = 0, {}
    while at + 8 <= len(raw):
        name, size = struct.unpack_from('<4sI', raw, at)
        at += 8
        if size > len(raw) - at:
            raise ValueError('Truncated CHK section')
        result[name] = raw[at:at + size]
        at += size
    return result


def prepare(item, tilesets, folder):
    source = Path(item['file'])
    if digest(source) != item['chkSha256']:
        raise ValueError('Map identity changed')
    c = chunks(source.read_bytes())
    w, h = struct.unpack('<HH', c[b'DIM '])
    era = struct.unpack('<H', c[b'ERA '])[0] & 7
    cv5 = (tilesets / (TILESETS[era] + '.cv5')).read_bytes()
    vf4 = (tilesets / (TILESETS[era] + '.vf4')).read_bytes()
    tiles = struct.unpack_from('<' + 'H' * (w * h), c[b'MTXM'])
    walk, build = bytearray(w * h * 16), bytearray(w * h)
    for y in range(h):
        for x in range(w):
            tile = tiles[y * w + x]
            at = ((tile >> 4) & 0x7ff) * 52
            mega = struct.unpack_from('<H', cv5, at + 20 + (tile & 15) * 2)[0]
            build[y * w + x] = not (cv5[at + 2] & 128)
            for sy in range(4):
                for sx in range(4):
                    flag = struct.unpack_from('<H', vf4, mega * 32 + (sy * 4 + sx) * 2)[0]
                    walk[(y * 4 + sy) * w * 4 + x * 4 + sx] = flag & 1
    # Same inaccessible bottom boundary as BWAPI/BWTA's offline reader.
    for y in range(h * 4 - 4, h * 4):
        walk[y * w * 4:(y + 1) * w * 4] = bytes(w * 4)
    for y in range(h * 4 - 8, h * 4 - 4):
        for x in list(range(20)) + list(range(w * 4 - 20, w * 4)):
            walk[y * w * 4 + x] = 0
    units = []
    raw_units = c.get(b'UNIT', b'')
    if len(raw_units) % 36:
        raise ValueError('Invalid UNIT section')
    for at in range(0, len(raw_units), 36):
        x, y, kind = struct.unpack_from('<HHH', raw_units, at + 4)
        resources = struct.unpack_from('<I', raw_units, at + 20)[0]
        units.append((kind, x, y, resources))
    # THG2 sprites that represent units, not ordinary decorative sprites.
    for at in range(0, len(c.get(b'THG2', b'')), 10):
        kind, x, y, owner, unused, flags = struct.unpack_from('<HHHBBH', c[b'THG2'], at)
        if not flags & 4096:
            units.append((kind, x, y, 0))
    folder.mkdir(parents=True, exist_ok=True)
    binary = folder / 'input.bin'
    binary.write_bytes(struct.pack('<III', 0x31424e4e, w, h) + walk + build + struct.pack('<I', len(units)) + b''.join(struct.pack('<IIII', *u) for u in units))
    details = dict(name=item['name'], mapHash=item['bwapiMapHashes'][0], chkSha256=item['chkSha256'],
                   width=w, height=h, tileset=TILESETS[era], inputSha256=digest(binary),
                   walkRows=[''.join(str(v) for v in walk[y * w * 4:(y + 1) * w * 4]) for y in range(h * 4)],
                   buildRows=[''.join(str(v) for v in build[y * w:(y + 1) * w]) for y in range(h)],
                   units=[dict(type=t, x=x, y=y, resources=r) for t, x, y, r in units],
                   tilesetSha256={'cv5': digest(tilesets / (TILESETS[era] + '.cv5')), 'vf4': digest(tilesets / (TILESETS[era] + '.vf4'))})
    (folder / 'input.json').write_text(json.dumps(details), encoding='utf-8')
    return binary, details


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tilesets', type=Path, required=True)
    p.add_argument('--only')
    p.add_argument('--rebuild',action='store_true')
    a = p.parse_args()
    executable = ROOT / 'build/terrain-build/Release/nnb-terrain.exe'
    for item in read_json(ROOT / 'data/maps.json'):
        if a.only and item['name'] != a.only:
            continue
        folder = ROOT / 'data/terrain' / item['bwapiMapHashes'][0]
        binary, details = prepare(item, a.tilesets, folder)
        cache=folder/'bwapi-data/BWTA2'/(details['mapHash']+'.bwta')
        if a.rebuild and cache.exists():
            stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            cache.rename(cache.with_suffix('.saved-'+stamp))
            if (folder/'geometry.json').exists():
                (folder/'geometry.json').rename(folder/('geometry.saved-'+stamp+'.json'))
        with (folder / 'analysis.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([str(executable), str(binary), details['mapHash']], cwd=folder, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        print(item['name'], 'exit', result.returncode, flush=True)
        if result.returncode:
            raise RuntimeError('Terrain analysis failed: ' + str(folder / 'analysis.log'))
        checker=ROOT/'build/terrain-build/Release/nnb-terrain-check.exe'
        with (folder/'verify.log').open('w',encoding='utf-8') as log:
            check=subprocess.run([str(checker),str(binary),details['mapHash']],cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        if check.returncode:raise RuntimeError('Native cache load/geometry check failed: '+str(folder/'verify.log'))
        manifest=dict(analyzerSha256=digest(executable),checkerSha256=digest(checker),cacheSha256=digest(cache),inputSha256=digest(binary),chkSha256=item['chkSha256'],startAnchors='Exact CHK starts applied before connectivity and distance calculation',nativeGameTested=False)
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
