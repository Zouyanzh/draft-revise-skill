#!/usr/bin/env python3
"""Install the repository skill with backup and version/commit provenance."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts
            and p.suffix != '.pyc' and p.name not in {'.DS_Store', '.release.json'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    parser.add_argument('--dest', type=Path, default=home / 'skills/draft-revise')
    args = parser.parse_args()
    dest = args.dest.expanduser().absolute()
    source = ROOT / 'draft-revise'
    if dest.resolve() == source.resolve() or source.resolve() in dest.resolve().parents:
        raise ValueError('Install target must be outside repository source')
    provenance = {'version': (ROOT / 'VERSION').read_text().strip(), 'commit': git('rev-parse', 'HEAD'),
                  'dirty': bool(git('status', '--porcelain')), 'source_repository': str(ROOT),
                  'installed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.draft-revise-install-', dir=str(dest.parent)))
    try:
        prepared = stage / 'draft-revise'
        shutil.copytree(source, prepared, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        assert files(prepared) == files(source)
        (prepared / '.release.json').write_text(json.dumps(provenance, indent=2) + '\n')
        backup = None
        if dest.exists() or dest.is_symlink():
            folder = dest.parent.parent / 'skill-backups'
            folder.mkdir(exist_ok=True)
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = folder / ('draft-revise-' + stamp)
            dest.rename(backup)
        try:
            prepared.rename(dest)
        except Exception:
            if backup:
                backup.rename(dest)
            raise
        assert files(dest) == files(source)
        print(json.dumps({'installed': str(dest), 'backup': str(backup) if backup else None, **provenance}, indent=2))
    finally:
        shutil.rmtree(stage)


if __name__ == '__main__':
    main()
