#!/usr/bin/env python3
"""Build deterministic, portable skill archives from tracked release inputs."""
import gzip
import hashlib
import io
from pathlib import Path
import re
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', version):
        raise ValueError('Invalid VERSION')
    prefix = 'draft-revise-v' + version
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    files = [ROOT / p for p in ['README.md', 'CONTRIBUTING.md', 'CHANGELOG.md', 'LICENSE', 'VERSION',
                               'requirements.txt', 'requirements-dev.txt', 'package.json', 'package-lock.json']]
    for folder in ['draft-revise', 'docs', 'tools', '.github']:
        files += [p for p in (ROOT / folder).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != '.DS_Store']
    files.sort(key=lambda p: p.relative_to(ROOT).as_posix())
    payload = {prefix + '/' + p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    zpath = dist / (prefix + '.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in payload.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    tpath = dist / (prefix + '.tar.gz')
    with tpath.open('wb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w') as tar:
                for name, data in payload.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o644
                    tar.addfile(info, io.BytesIO(data))
    with zipfile.ZipFile(zpath) as z:
        assert {n: z.read(n) for n in z.namelist()} == payload
    with tarfile.open(tpath) as tar:
        assert {m.name: tar.extractfile(m).read() for m in tar.getmembers()} == payload
    sums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in [zpath, tpath])
    (dist / 'SHA256SUMS').write_text(sums, encoding='utf-8')
    print('Built and verified archives with ' + str(len(payload)) + ' files each')
    print(sums, end='')


if __name__ == '__main__':
    main()
