#!/usr/bin/env python3
"""Creator index, validation, bundle and composition preview; no printer access."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_printer_catalog import Catalog,digest
from sv08_printer_definitions import validate_definition,public_json,FORMAT,FILE_LIMIT,MAX_DEFINITIONS
from sv08_printer_sources import validate_manifest,relative,bundle_preview
from sv08_printer_compose import select_definition
from sv08_printer_compact import compile_records
from sv08_printer_generate import generate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['validate','index','bundle','preview']);p.add_argument('directory',type=Path)
    p.add_argument('--installation',type=Path);p.add_argument('--definition');p.add_argument('--mode',choices=['sensors','full'],default='sensors');a=p.parse_args()
    catalog=Catalog(Path(__file__).resolve().parents[1]/'catalog/printer/catalog.json')
    if a.directory.is_symlink():raise ValueError('Catalogue root must be a regular directory')
    root=a.directory.resolve()
    def read(name):
        path=root/relative(name)
        if any(x.is_symlink() for x in [path,*path.parents]) or not path.is_file() or path.stat().st_size>FILE_LIMIT:raise ValueError('Catalogue files must be bounded regular files')
        return path.read_bytes()
    manifest=public_json(read('catalog.json'));entries=[]
    paths=sorted(str(f.relative_to(root)) for f in (root/'definitions').rglob('*.json')) if a.operation=='index' else [row['path'] for row in manifest['definitions']]
    if not 1<=len(paths)<=MAX_DEFINITIONS:raise ValueError('Definition count must be 1–32')
    files={};authored=[]
    for name in paths:
        raw=read(name);d=public_json(raw)
        authored.append(d)
        files[name]=base64.b64encode(raw).decode()
        entries.append(dict(id=d['id'],version=d['version'],path=name,sha256=hashlib.sha256(raw).hexdigest()))
    compiled,errors=compile_records(authored,catalog)
    if errors:raise ValueError('; '.join(ident+': '+reason for ident,reason in errors.items()))
    if a.operation=='index':
        manifest['format_version']=FORMAT;manifest['definitions']=entries;validate_manifest(manifest)
        (root/'catalog.json').write_text(json.dumps(manifest,indent=2)+'\n')
    else:
        validate_manifest(manifest)
        if manifest['definitions']!=entries:raise ValueError('Index differs from files; run index after edits')
    bundle=dict(manifest=manifest,files=files)
    if a.operation=='bundle':result=bundle
    elif a.operation=='preview':
        if not a.installation or not a.definition:raise ValueError('Preview needs --installation and --definition')
        source=bundle_preview(bundle,catalog);d=next((r for r in source['records'] if r['id']==a.definition),None)
        if not d:raise ValueError('Supported definition ID required')
        ref=dict(source=source['id'],id=d['id'],version=d['version'],sha256=digest(d),commit=source['commit'])
        snapshots={source['id']+'::'+r['id']+'@'+r['version']:r for r in source['records']}
        from sv08_printer_definitions import builtins
        snapshots.update({'builtin::'+r['id']+'@'+r['version']:r for r in builtins(catalog)})
        draft=select_definition(catalog,public_json(a.installation.read_bytes()),ref,snapshots)
        result=dict(draft=draft,output=generate(catalog,draft,a.mode),hardware=False)
    else:result=dict(passed=True,definitions=len(entries),format=FORMAT,hardware=False)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError) as error:print(str(error),file=sys.stderr);sys.exit(1)
