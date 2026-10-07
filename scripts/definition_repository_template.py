#!/usr/bin/env python3
"""Deterministic, public-only repository ZIP built offline during UI staging."""
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

REPO = Path(__file__).resolve().parents[1]
FILENAME = 'definition-repository-starter.zip'
PREFIX = 'printer-definition-repository/'
SCHEMA_FILENAME = 'definition-schema-reference.zip'
SCHEMA_PREFIX = 'definition-schema-reference/'
SCHEMAS = ('assembly', 'behaviour', 'board', 'catalog', 'compact', 'component', 'connection', 'definition')

def reference_files(repo):
    # Explicit public inputs only; no host state or generated printer configuration.
    files = {'schemas/'+name+'.schema.json': (repo/'schemas/printer-definitions/v1'/ (name+'.schema.json')).read_bytes() for name in SCHEMAS}
    files['LICENSE'] = (repo/'examples/printer-definitions/LICENSE').read_bytes()
    files['README.md'] = (repo/'scripts/definition_repository_template/schema-reference.md').read_bytes()
    guide = (repo/'docs/development/printer-public-format.md').read_text()
    import re
    def public_link(match):
        target = match.group(1)
        if target.startswith(('https:', '#')): return match.group(0)
        path = (repo/'docs/development'/target).resolve().relative_to(repo.resolve())
        return '(https://github.com/drew442/sv08-mainline/blob/main/'+str(path)+')'
    files['public-format.md'] = re.sub(r'(?<=\])\(([^()\s]+)\)', public_link, guide).encode()
    files['field-registry.py'] = (repo/'runtime/sv08_printer_fields.py').read_bytes()
    return files

def schema_archive(repo=REPO):
    return zip_files(reference_files(Path(repo)), SCHEMA_PREFIX)



def archive(repo=REPO):
    repo = Path(repo)
    examples = repo / 'examples/printer-definitions'
    templates = repo / 'scripts/definition_repository_template'
    files = {name: (examples / name).read_bytes() for name in ['LICENSE','fixtures/installation.json']}
    fixture=json.loads(files['fixtures/installation.json']);fixture['boards']['tool']={'id':'sv08-tool'}
    files['fixtures/installation.json']=(json.dumps(fixture,indent=2)+'\n').encode()
    definitions = {
        'board': dict(id='my-mainboard', name='Factory mainboard example', version='1.0.0', extends='sv08.factory.mainboard'),
        'bed': dict(id='my-bed', name='Bed temperature limit example', version='1.0.0', extends='sv08.factory.hotbed', heater_bed={'max_temp':105}),
        'assembly': dict(id='my-bed-and-probe', name='Bed and probe bundle example', version='1.0.0', extends=['my-bed','sv08.factory.probe']),
        'behaviour': dict(id='my-levelling-policy', name='No additional levelling check example', version='1.0.0', category='bed', advanced={'behaviours':[dict(hook='levelling.preconditions',operation='none',sources=['author'])]})}
    import hashlib
    entries=[]
    for name,value in sorted(definitions.items()):
        path='definitions/'+name+'.json';raw=(json.dumps(value,indent=2)+'\n').encode();files[path]=raw
        entries.append(dict(id=value['id'],version=value['version'],path=path,sha256=hashlib.sha256(raw).hexdigest()))
    manifest=dict(format_version='0.1',catalog_id='my-printer-definitions',name='My printer definitions',publisher={'name':'Your name'},license='GPL-3.0-or-later',definitions=entries)
    files['catalog.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    files.update({'AGENTS.md': (templates / 'AGENTS.md').read_bytes(),
                  'README.md': (templates / 'README.md').read_bytes(),
                  '.gitignore': (templates / 'gitignore').read_bytes(),
                  'tools/update_catalog.py': (templates / 'update_catalog.py').read_bytes()})
    files.update({'reference/'+name: raw for name, raw in reference_files(repo).items()})
    return zip_files(files, PREFIX)


def zip_files(files, prefix):
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as target:
        for name, raw in sorted(files.items()):
            entry = ZipInfo(prefix + name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = ZIP_DEFLATED
            target.writestr(entry, raw, compresslevel=9)
    return output.getvalue()


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--schemas':
        Path(sys.argv[2]).write_bytes(schema_archive())
        raise SystemExit(0)
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python3 scripts/definition_repository_template.py [--schemas] OUTPUT.zip')
    Path(sys.argv[1]).write_bytes(archive())
