#!/usr/bin/env python3
"""Validate distributable skill metadata and repository release inputs."""
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    assert re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', version), 'Invalid VERSION'
    skill = ROOT / 'draft-revise'
    text = (skill / 'SKILL.md').read_text(encoding='utf-8')
    header = yaml.safe_load(text.split('---', 2)[1])
    assert header['name'] == skill.name
    assert isinstance(header.get('description'), str) and header['description'].strip()
    ui = yaml.safe_load((skill / 'agents/openai.yaml').read_text(encoding='utf-8'))
    assert ui['interface']['display_name']
    assert not ui.get('policy', {}).get('allow_implicit_invocation') is False
    for link in re.findall(r'\]\(([^)]+)\)', text):
        if '://' not in link and not link.startswith('#'):
            assert (skill / link.split('#')[0]).is_file(), 'Missing reference: ' + link
    for name in ['README.md', 'CHANGELOG.md', 'LICENSE', 'docs/releases/v' + version + '.md']:
        assert (ROOT / name).is_file(), 'Missing release input: ' + name
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'Codex' in readme and '## English' in readme and '## 中文' in readme
    print('Codex skill metadata and release inputs are valid: v' + version)


if __name__ == '__main__':
    main()
