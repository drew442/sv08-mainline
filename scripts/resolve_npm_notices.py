#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verify exact-version supplemental upstream notices; never synthesize licenses.

Research inputs reference locally retained public supplier responses. Output
embeds exact original UTF-8 response/text bytes and hashes, so it is portable.
Sibling package notices do not establish coverage for a monorepo package.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from urllib.parse import unquote, urlsplit
from license_inventory import digest, serialize

REVISION = re.compile(r'[0-9a-f]{40}')


def retained(pin):
    raw = Path(pin['path']).read_bytes()
    if len(raw) > 4*1024*1024 or digest(raw) != pin['sha256']:
        raise ValueError('Supplemental evidence bytes/hash mismatch')
    return dict(url=pin['url'],sha256=digest(raw),text=raw.decode('utf-8'))


def text_pin(pin):
    raw = pin['text'].encode('utf-8')
    if not raw.strip() or digest(raw) != pin['sha256']:
        raise ValueError('Supplemental evidence text/hash mismatch')
    return raw


def repository(value):
    if isinstance(value,dict): value=value.get('url','')
    value = (value or '').removeprefix('git+').removesuffix('.git')
    for prefix in ('https://github.com/','git://github.com/','git@github.com:'):
        if value.startswith(prefix):
            value=value[len(prefix):]
            if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',value): return value
    raise ValueError('Supported exact upstream GitHub repository required')


def archive_sources(path, include_code=False):
    code={};metadata=None;total=0
    with tarfile.open(path) as archive:
        for member in archive:
            relative=PurePosixPath(member.name)
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe supplier source member')
            if not member.isfile(): continue
            if len(relative.parts)==2 and relative.name=='package.json':
                if metadata is not None or member.size>1024*1024: raise ValueError('Invalid primary metadata')
                metadata=json.load(archive.extractfile(member))
            elif include_code and relative.suffix.lower() in ('.js','.cjs','.mjs','.ts','.tsx','.jsx','.json','.wasm','.node'):
                total+=member.size
                if member.size>16*1024*1024 or total>64*1024*1024: raise ValueError('Source comparison exceeds bound')
                code[member.name]=digest(archive.extractfile(member).read())
    return metadata,code


def code_equivalence(record, archive_path, prefix):
    if archive_path is None: raise ValueError('Actual archive required for source equivalence')
    metadata,code=archive_sources(archive_path,True);matched={}
    for comparison in record.get('source_package_comparisons',[]):
        pin=comparison['source'];raw=text_pin(pin)
        if not pin['url'].startswith(prefix): raise ValueError('Source comparison commit mismatch')
        member=comparison['archive_member']
        if member in code:
            if digest(raw)!=code[member]: raise ValueError('Shipped source bytes differ from notice source')
            if member in matched: raise ValueError('Duplicate source comparison member')
            matched[member]=code[member]
    if not code or set(matched)!=set(code): raise ValueError('Incomplete shipped executable source byte coverage')
    return True


def later_notice_equivalence(record, original, prefix):
    pin=record.get('source_tree_comparison')
    if not pin: raise ValueError('Later notice requires authoritative source tree comparison')
    response=json.loads(text_pin(pin));repo=record['source_repository'];revision=record['source_revision']
    expected='https://api.github.com/repos/'+repo+'/compare/'+original+'...'+revision
    if pin['url']!=expected or response['base_commit']['sha']!=original or response['commits'][-1]['sha']!=revision:
        raise ValueError('Source comparison revision mismatch')
    if response.get('total_commits')!=len(response['commits']) or len(response.get('files',[]))!=1:
        raise ValueError('Incomplete or changed source comparison')
    change=response['files'][0]
    if change.get('filename')!='LICENSE' or change.get('status')!='added':
        raise ValueError('Later notice changed preexisting source')
    if not any(p['url']==prefix+'LICENSE' for p in record['notices']): raise ValueError('Compared notice not supplied')
    return True


def validate_record(record, name, version, integrity, archive_sha256, archive_path=None):
    if (record['name'],record['version'],record['integrity'],record['archive_sha256']) != (name,version,integrity,archive_sha256):
        raise ValueError('Supplemental notice dependency identity mismatch')
    metadata = json.loads(text_pin(record['registry_metadata']))
    url = urlsplit(record['registry_metadata']['url'])
    if (url.scheme,url.netloc,unquote(url.path),url.query,url.fragment) != ('https','registry.npmjs.org','/'+name+'/'+version,'',''):
        raise ValueError('Exact-version authoritative registry endpoint required')
    if (metadata['name'],metadata['version'],metadata['dist']['integrity']) != (name,version,integrity):
        raise ValueError('Registry package identity/integrity mismatch')
    revision=record['source_revision']; repo=record['source_repository']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo): raise ValueError('Unsafe upstream repository')
    if not REVISION.fullmatch(revision): raise ValueError('Exact source commit required')
    declared_repo=metadata.get('repository')
    if declared_repo:
        if repository(declared_repo) != repo: raise ValueError('Registry upstream repository mismatch')
    else:
        homepage=urlsplit(str(metadata.get('homepage','')))
        if homepage.scheme not in ('https','http') or homepage.netloc!='github.com' or homepage.path.rstrip('/')!='/'+repo:
            raise ValueError('Registry lacks matching upstream repository/homepage')
    prefix='https://raw.githubusercontent.com/'+repo+'/'+revision+'/'
    directory=PurePosixPath('.')
    archive_metadata=archive_sources(archive_path)[0] if archive_path else {}
    archive_commit=(archive_metadata or {}).get('buildInfo',{}).get('commitSha')
    discrepancy=None
    source_pin=record.get('source_package_metadata')
    if source_pin:
        source=json.loads(text_pin(source_pin))
        if not source_pin['url'].startswith(prefix) or not source_pin['url'].endswith('/package.json'):
            raise ValueError('Source package metadata must use pinned upstream commit')
        if source['name']!=name:
            if metadata.get('gitHead')!=revision or source['version']!=version:
                raise ValueError('Source package name/version mismatch')
            code_equivalence(record,archive_path,prefix)
            discrepancy=dict(registry_name=name,source_name=source['name'],version=version,
                             verification='exact-registry-gitHead-and-complete-shipped-executable-source-byte-equality')
        elif source['version']!=version and archive_commit!=revision:
            raise ValueError('Source package name/version mismatch')
        directory=PurePosixPath(source_pin['url'][len(prefix):]).parent
    method='registry-gitHead'
    if metadata.get('gitHead'):
        if metadata['gitHead'] != revision:
            later_notice_equivalence(record,metadata['gitHead'],prefix)
            method='later-author-notice; preexisting-source-unchanged'
    elif archive_commit == revision:
        ref=record['version_reference'];response=json.loads(text_pin(ref))
        if ref['url'] not in {'https://api.github.com/repos/'+repo+'/commits/'+tag for tag in (version,'v'+version)} or response['sha']!=revision:
            raise ValueError('Archive build commit/tag mismatch')
        method='archive-build-commit-and-version-tag'
    elif record.get('source_package_comparisons'):
        if source_pin is None: raise ValueError('Source equivalence requires source package identity')
        code_equivalence(record,archive_path,prefix)
        method='exact-shipped-executable-source-bytes; supplemental-author-notice'
    else:
        if source_pin is None: raise ValueError('Version tag requires source package identity')
        ref=record['version_reference']; response=json.loads(text_pin(ref))
        if ref['url'] not in {'https://api.github.com/repos/'+repo+'/commits/'+tag for tag in (version,'v'+version)} or response['sha'] != revision:
            raise ValueError('Exact version tag/source commit mismatch')
        method='exact-version-tag-and-source-package'
    if not record['notices']: raise ValueError('Missing authoritative notice text')
    for notice in record['notices']:
        text_pin(notice)
        if not notice['url'].startswith(prefix):
            reference=record.get('referenced_source_notice')
            if not reference or not reference['url'].startswith(prefix): raise ValueError('Notice source commit mismatch')
            reference_text=text_pin(reference).decode('utf-8')
            parsed=urlsplit(notice['url'])
            if parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Anonymous author notice HTTPS URL required')
            if notice['url'] not in reference_text and notice['url'].replace('https://','http://',1) not in reference_text:
                raise ValueError('Pinned source does not explicitly reference author notice')
            relative=PurePosixPath(reference['url'][len(prefix):])
            method+='; pinned-source-references-author-document'
        else: relative=PurePosixPath(notice['url'][len(prefix):])
        if relative.is_absolute() or '..' in relative.parts or relative.parent not in (directory,*directory.parents):
            raise ValueError('Sibling/unrelated source notice does not establish package coverage')
    if discrepancy: method+='; source-package-name-alias-with-exact-code-equality'
    result=dict(record,source_mapping=method)
    if discrepancy: result['source_package_identity_discrepancy']=discrepancy
    return result


def archive_identity(path, integrity, name, version):
    raw=Path(path).read_bytes()
    tokens=dict(token.split('-',1) for token in integrity.split())
    algorithm=next((a for a in ('sha512','sha384','sha256') if a in tokens),None)
    if not algorithm or hashlib.new(algorithm,raw).digest() != base64.b64decode(tokens[algorithm],validate=True):
        raise ValueError('Supplier archive SRI mismatch')
    with tarfile.open(path) as archive:
        members=archive.getmembers()
        if any(PurePosixPath(m.name).is_absolute() or '..' in PurePosixPath(m.name).parts for m in members):
            raise ValueError('Unsafe supplier archive path')
        if len({m.name for m in members}) != len(members): raise ValueError('Duplicate supplier archive member')
        primary=[m for m in members if m.isfile() and len(PurePosixPath(m.name).parts)==2 and m.name.endswith('/package.json')]
        if len(primary)!=1 or primary[0].size > 1024*1024: raise ValueError('Invalid supplier package metadata')
        package=json.load(archive.extractfile(primary[0]))
        if (package['name'],package['version']) != (name,version): raise ValueError('Supplier archive identity mismatch')
    return digest(raw)


def resolve(records, expected=None):
    if expected is None:
        baseline=json.loads((Path(__file__).resolve().parents[1]/'configs/host/source-license-inventory.json').read_text())
        expected={p['path']:(p['name'],p['version'],p['integrity'],p['archive']['sha256'])
                  for p in baseline['mainsail_dependencies']['packages'] if not p['notices']}
        if len(expected)!=69: raise ValueError('Historical declaration-only baseline must contain exactly 69 dependencies')
    if {item['path'] for item in records} != set(expected):
        raise ValueError('Research must exactly cover the historical declaration-only dependency set')
    accepted=[]; unresolved=[]; seen=set()
    for item in sorted(records,key=lambda x:x['path']):
        if item['path'] in seen: raise ValueError('Duplicate dependency supplemental evidence')
        seen.add(item['path'])
        try:
            record={k:item[k] for k in ('path','name','version','integrity','source_revision')}
            record['archive_sha256']=archive_identity(item['local_archive'],item['integrity'],item['name'],item['version'])
            if (item['name'],item['version'],item['integrity'],record['archive_sha256']) != expected[item['path']]:
                raise ValueError('Historical dependency identity/archive mismatch')
            record['source_repository']=item['source_repository_normalized']
            record['registry_metadata']=retained(item['registry_metadata'])
            if item.get('source_package_metadata'):
                record['source_package_metadata']=retained(item['source_package_metadata'])
            if 'version_reference' in item: record['version_reference']=retained(item['version_reference'])
            if item.get('referenced_source_notice'): record['referenced_source_notice']=retained(item['referenced_source_notice'])
            if item.get('source_tree_comparison'): record['source_tree_comparison']=retained(item['source_tree_comparison'])
            if item.get('source_package_comparisons'):
                record['source_package_comparisons']=[dict(archive_member=p['archive_member'],source=retained(p['source']))
                    for p in item['source_package_comparisons']]
            if item.get('limitation'): record['limitation']=item['limitation']
            if item.get('release_generation_sources'):
                record['release_generation_sources']=[retained(p) for p in item['release_generation_sources']]
            record['notices']=[retained(p) for p in item['notices']]
            accepted.append(validate_record(record,item['name'],item['version'],item['integrity'],record['archive_sha256'],item['local_archive']))
        except (ValueError,KeyError,OSError,TypeError) as error:
            unresolved.append(dict(path=item['path'],name=item['name'],version=item['version'],reason=str(error)))
    return dict(format_version=1,scope='exact-version-upstream-supplemental-notices',
        legal_compliance_assessed=False,records=accepted,unresolved=unresolved,
        coverage=dict(inspected=len(records),resolved=len(accepted),unresolved=len(unresolved)))


def notice_text(result):
    chunks=[]
    for record in result['records']:
        chunks.append(record['name']+'@'+record['version']+'\n')
        for pin in record['notices']:
            chunks.extend([pin['url']+'\n',pin['text'],'\n'])
    return '\n'.join(chunks)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--text-output')
    args=parser.parse_args()
    try:
        for output in (args.output,args.text_output):
            if output and not Path(output).parent.is_dir(): raise ValueError('Output parent directory must exist')
        result=resolve(json.loads(Path(args.research).read_text()))
        Path(args.output).write_text(serialize(result))
        if args.text_output: Path(args.text_output).write_text(notice_text(result))
        print(json.dumps(result['coverage'],sort_keys=True))
        if result['unresolved']: parser.exit(1,'Unresolved exact-version notice evidence remains\n')
    except (ValueError,OSError,KeyError,TypeError) as error: parser.exit(1,str(error)+'\n')

if __name__=='__main__': main()
