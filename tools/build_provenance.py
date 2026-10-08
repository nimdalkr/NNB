"""Bind an editor DLL to the exact local gameplay sources used to build it."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'build/editor-build.json'


def source_digest():
    files = list(ROOT.glob('*.sln'))
    extensions = {'.cpp', '.c', '.h', '.hpp', '.vcxproj', '.props', '.def'}
    for name in ('Steamhammer', 'BOSS', 'BWAPILIB', 'BWTA', 'BWEM', 'BWEB'):
        files.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and p.suffix in extensions)
    h = hashlib.sha256()
    for path in sorted(files):
        h.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def check(dll):
    if not MANIFEST.exists():
        raise ValueError('scripts/build-editor.ps1로 편집용 DLL을 빌드하고 검증하세요')
    record = json.loads(MANIFEST.read_text())
    if record['sourceSha256'] != source_digest() or record['dllSha256'] != hashlib.sha256(dll.read_bytes()).hexdigest():
        raise ValueError('소스와 실행 DLL이 다릅니다. scripts/build-editor.ps1을 다시 실행하세요')
    return record


if __name__ == '__main__':
    dll = ROOT/'Release/Locutus.dll'
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({'sourceSha256':source_digest(), 'dllSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),
                                   'nativeGameTested':False}, indent=2))
