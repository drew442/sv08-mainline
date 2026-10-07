#!/usr/bin/env python3
"""Refresh local pinned dependency digests and catalogue file hashes. Python 3 only."""
import hashlib
import json
from pathlib import Path
import sys


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON value')))


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def refresh(root):
    root = root.absolute()
    paths = sorted((root / 'definitions').rglob('*.json'))
    if not 1 <= len(paths) <= 32:
        raise ValueError('Expected 1–32 definition JSON files')
    records = {}
    for path in [root / 'catalog.json', *paths]:
        if any(p.is_symlink() for p in [path, *path.parents]) or not path.is_file():
            raise ValueError('Use regular files and directories, without symlinks')
        if path.stat().st_size > 128 * 1024:
            raise ValueError('Definition file exceeds 128 KiB')
        if path.name == 'catalog.json' and path.parent == root:
            continue
        value = read_json(path)
        key = (value['id'], value['version'])
        if key in records:
            raise ValueError('Duplicate definition ID/version: ' + str(key))
        records[key] = (path, value)
    manifest = read_json(root / 'catalog.json')
    # Compact local inheritance needs no hand-written dependency hashes.
    by_id={value['id']:key for key,(_,value) in records.items()}
    if len(by_id)!=len(records):raise ValueError('Only one version per definition ID can be indexed')
    inheritance=set();checked=set()
    def check_base(key,depth=0):
        if depth>12 or key in inheritance:raise ValueError('Compact inheritance cycle or depth exceeds 12')
        if key in checked:return
        inheritance.add(key)
        value=records[key][1];refs=value.get('extends',[]);refs=[refs] if isinstance(refs,str) else refs
        if not isinstance(refs,list) or not all(isinstance(ref,str) for ref in refs):raise ValueError('extends must be a name or list')
        for ref in refs:
            if ref in by_id:check_base(by_id[ref],depth+1)
            elif not ref.startswith(('sv08.factory','sv08-main.','sv08-tool.')):raise ValueError('Local inheritance base missing: '+ref)
        inheritance.remove(key);checked.add(key)
    for key in records:check_base(key)
    visiting, digests = set(), {}

    def resolve(key, depth=0):
        if depth > 12 or key in visiting:
            raise ValueError('Local dependency cycle or depth exceeds 12: ' + str(key))
        if key in digests:
            return digests[key]
        if key not in records:
            raise ValueError('Local dependency missing; update its ID/version: ' + str(key))
        visiting.add(key)
        value = records[key][1]
        for dependency in value.get('dependencies', []):
            # Explicit external sources retain the publisher's pinned digest.
            if 'source' not in dependency:
                target=records.get((dependency['id'],dependency['version']))
                if target and 'kind' not in target[1]:raise ValueError('Use compact extends for compact local bases; expanded dependency digests require the SV08 validator')
                dependency['sha256'] = resolve((dependency['id'], dependency['version']), depth + 1)
        visiting.remove(key)
        digests[key] = canonical_digest(value)
        return digests[key]

    for key in records:
        resolve(key)
    contents = {path: (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
                for path, value in records.values()}
    manifest['definitions'] = [dict(id=value['id'], version=value['version'],
                                   path=path.relative_to(root).as_posix(),
                                   sha256=hashlib.sha256(contents[path]).hexdigest())
                               for path, value in records.values()]
    manifest_bytes = (json.dumps(manifest, indent=2, allow_nan=False) + '\n').encode()
    if any(len(raw) > 128 * 1024 for raw in [*contents.values(), manifest_bytes]):
        raise ValueError('Formatted file exceeds 128 KiB')
    # All parsing/dependency checks finish before any authoring file changes.
    for path, raw in contents.items():
        path.write_bytes(raw)
    (root / 'catalog.json').write_bytes(manifest_bytes)
    return len(records)


if __name__ == '__main__':
    try:
        root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1]
        if len(sys.argv) > 2:
            raise ValueError('Usage: python3 tools/update_catalog.py [repository-directory]')
        print('Refreshed', refresh(root), 'definitions. Run the SV08 creator validator before publishing.')
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
