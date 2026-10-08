"""Prepare pinned, isolated offline analyzer dependencies; preserve bot sources."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
DEPS=ROOT/'build/deps'
PACKAGES=[
 ('CGAL-5.6.1.tar.xz','https://github.com/CGAL/cgal/releases/download/v5.6.1/CGAL-5.6.1.tar.xz','cdb15e7ee31e0663589d3107a79988a37b7b1719df3d24f2058545d1bcdd5837','CGAL-5.6.1'),
 ('boost_1_83_0.7z','https://archives.boost.io/release/1.83.0/source/boost_1_83_0.7z','22ee9dcf3f1fb58f585772f70c69113a4077b92adeac58b643b3543b78633a16','boost_1_83_0'),
 ('gmp-mpfr.zip','https://github.com/CGAL/cgal/releases/download/v5.6.1/CGAL-5.6.1-win64-auxiliary-libraries-gmp-mpfr.zip','91b10cf8e3cf830f52103d3669a1084399086b03e29c34fc157c7c6605936c27','auxiliary'),
]


def main():
    DEPS.mkdir(parents=True,exist_ok=True)
    for name,url,sha,folder in PACKAGES:
        p=DEPS/name
        if not p.exists():urllib.request.urlretrieve(url,p)
        if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError('Dependency hash mismatch: '+name)
        if not (DEPS/folder).exists():subprocess.run(['tar','-xf',str(p),'-C',str(DEPS)],check=True)
    source=DEPS/'bwta2-v22'
    if not source.exists():subprocess.run(['git','clone','--depth','1','--branch','v2.2','https://bitbucket.org/auriarte/bwta2.git',str(source)],check=True)
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if head!='b2bac87bbaa0a2a209b3b5deb276d657fdc656ae':raise ValueError('Unexpected BWTA source')
    prepared=ROOT/'build/terrain-source'
    patch=ROOT/'tools/terrain-build/bwta-compat.patch'
    if not prepared.exists():
        shutil.copytree(source,prepared,ignore=shutil.ignore_patterns('.git','lib','maps'))
        subprocess.run(['git','apply','--no-index',str(patch)],cwd=prepared,check=True)
    else:
        # Do not replace a possibly changed work folder. Verify our patch is present.
        subprocess.run(['git','apply','--no-index','--reverse','--check',str(patch)],cwd=prepared,check=True)
    parabola=DEPS/'CGAL-5.6.1/include/CGAL/Parabola_segment_2.h'
    text=parabola.read_text()
    old='int(CGAL::to_double(CGAL::sqrt(tt / STEP)))'
    new='int(std::sqrt(CGAL::to_double(tt / STEP)))'
    if old not in text and new not in text:raise ValueError('Unexpected CGAL compatibility point')
    parabola.write_text(text.replace(old,new))
    print('Pinned analyzer dependencies ready. CGAL sampling-index compatibility and exact CHK start anchors applied.')


if __name__=='__main__':main()
