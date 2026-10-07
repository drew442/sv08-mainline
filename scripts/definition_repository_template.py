#!/usr/bin/env python3
"""Deterministic, public-only repository ZIP built offline during UI staging."""
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

REPO = Path(__file__).resolve().parents[1]
FILENAME = 'definition-repository-starter.zip'
PREFIX = 'printer-definition-repository/'


def archive(repo=REPO):
    repo = Path(repo)
    examples = repo / 'examples/printer-definitions'
    templates = repo / 'scripts/definition_repository_template'
    names = ['LICENSE', 'fixtures/installation.json', 'definitions/board.json',
             'definitions/bed.json', 'definitions/assembly.json', 'definitions/behaviour.json']
    files = {name: (examples / name).read_bytes() for name in names}
    manifest = json.loads((examples / 'catalog.json').read_bytes())
    manifest.update(catalog_id='my-printer-definitions', name='My printer definitions',
                    publisher={'name': 'Your name'})
    files['catalog.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    files.update({'README.md': (templates / 'README.md').read_bytes(),
                  '.gitignore': (templates / 'gitignore').read_bytes(),
                  'tools/update_catalog.py': (templates / 'update_catalog.py').read_bytes()})
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as target:
        for name, raw in sorted(files.items()):
            entry = ZipInfo(PREFIX + name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = ZIP_DEFLATED
            target.writestr(entry, raw, compresslevel=9)
    return output.getvalue()


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python3 scripts/definition_repository_template.py OUTPUT.zip')
    Path(sys.argv[1]).write_bytes(archive())
