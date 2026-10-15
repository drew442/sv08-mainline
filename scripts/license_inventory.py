#!/usr/bin/env python3
"""Generate a deterministic, source-bound inventory from explicit local inputs.

No downloads, SPDX inference, legal compliance assessment or source-build claims
for supplier binaries. --inputs is a coordinator-owned JSON manifest: applications
map each current configs/apps/*.json and configs/host-os/rauc-package.json to
{config_sha256, source_pin, artifact:{root,path,sha256}, notices:[file pins],
rebuild_evidence:[file pins]}; wheelhouses contain {root,lock,lock_sha256};
An application with no declared source license may instead supply notices:[],
license_status:"not-declared-in-inspected-source", source_artifact:file pin and
license_inspection:file pin for a JSON receipt containing that license_status,
source_sha256, nonempty inspected_paths and notices:[]. This unresolved declaration
is visible in output; it does not establish source licensing or a repository audit.
wheel_sources is keyed by artifact SHA256 and contains {name,version,source_pin,
classification,rebuild_evidence, supplemental_notices}. Every file pin is
{root,path,sha256}; notice pins additionally bind source_pin. mainsail contains
{root,path,sha256} for the selected patched package-lock.json, archive_notice_root,
and dependency_notices keyed by every lock package path. Each dependency entry is
{name,version,integrity,archive:file pin,package_json:file pin,notices:[file pins]};
copied metadata/notice pins include archive_member and use archive_notice_root.
The archive's SRI and copied text contents are verified before inventory inclusion.
An inspected archive without recognizable notice filenames may retain its verified
package.json license declaration alone, explicitly marked without embedded text.
debian_root is
the read-only documented baseline. build_tools contains equivalent source/artifact/
notice/proof records. Output contains content hashes, never transient absolute roots.
"""
import argparse
import base64
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
HASH = re.compile(r'[0-9a-f]{64}')
NOTICE = re.compile(r'^(licen[cs]e|copying|copyright|notice|authors)(?:[._-].*)?$', re.I)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def checked_path(root, relative):
    root = Path(root).resolve()
    relative = PurePosixPath(relative)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Unsafe relative input path')
    path = root / relative
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('Input escapes its root or is missing: ' + str(relative))
    return path


def file_pin(pin):
    path = checked_path(pin['root'], pin['path'])
    if sha(path) != pin['sha256']:
        raise ValueError('File hash mismatch: ' + pin['path'])
    return {'path': pin['path'], 'sha256': sha(path), 'bytes': path.stat().st_size}


def source_pin(pin):
    # A supplier source-index or provenance receipt is evidence of availability,
    # not a claim that the corresponding source was downloaded or compiled.
    if not pin.get('identity') or not pin.get('version'):
        raise ValueError('Source identity and version are required')
    if not (HASH.fullmatch(pin.get('sha256', '')) or re.fullmatch(r'[0-9a-f]{40}', pin.get('commit', ''))):
        raise ValueError('Source must have an exact archive/provenance hash or commit')
    if not pin.get('kind') in ('source-archive', 'source-file', 'git-commit', 'supplier-provenance'):
        raise ValueError('Explicit source pin kind required')
    result = {key: value for key, value in pin.items() if key != 'file'}
    if 'file' in pin:
        result['file'] = file_pin(pin['file'])
        if result['file']['sha256'] != pin.get('sha256'):
            raise ValueError('Source/provenance file differs from source pin')
    return result


def evidence(record):
    classification = record['classification']
    if classification not in ('project-source-build', 'upstream-binary'):
        raise ValueError('Explicit project-source-build or upstream-binary classification required')
    proofs = [file_pin(p) for p in record.get('rebuild_evidence', [])]
    if classification == 'project-source-build' and not proofs:
        raise ValueError('Project source-build requires explicit reusable proof')
    if classification == 'upstream-binary' and proofs:
        raise ValueError('Supplier binary packaging does not establish source rebuild proof')
    return {'classification': classification, 'rebuild_evidence': proofs,
            'source': source_pin(record['source_pin'])}


def notice_pin(pin):
    return dict(file_pin(pin), source=source_pin(pin['source_pin']))


def locked_wheels(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})', line)
        if not match or match[3] in result:
            raise ValueError('Require unique exact wheel lock entries')
        result[match[3]] = (normalize(match[1]), match[2])
    return result


def normalize(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def inspect_wheel(path, expected, provenance):
    artifact_hash = sha(path)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names) or any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):
            raise ValueError('Duplicate or unsafe wheel member')
        metadata = [n for n in names if re.fullmatch(r'[^/]+\.dist-info/METADATA', n)]
        if len(metadata) != 1:
            raise ValueError('Wheel needs exactly one top-level METADATA')
        message = BytesParser().parsebytes(archive.read(metadata[0]))
        name, version = message['Name'], message['Version']
        if not name or not version or (normalize(name), version) != expected or provenance['name'] != name or provenance['version'] != version:
            raise ValueError('Wheel metadata, lock and source provenance disagree')
        if provenance['source_pin']['version'] != version:
            raise ValueError('Wheel source provenance version mismatch')
        metadata_root = metadata[0].rsplit('/', 1)[0]
        license_fields = {key: message.get_all(key, []) for key in ('License', 'License-Expression', 'License-File')}
        notice_names = {n for n in names if not n.endswith('/') and NOTICE.match(PurePosixPath(n).name)}
        for declared in license_fields['License-File']:
            if PurePosixPath(declared).is_absolute() or '..' in PurePosixPath(declared).parts:
                raise ValueError('Unsafe declared license path')
            candidates = [metadata_root + '/' + declared, metadata_root + '/licenses/' + declared]
            found = [n for n in candidates if n in names]
            if not found:
                raise ValueError('Declared wheel notice missing: ' + declared)
            notice_names.update(found)
        notices = [{'path': n, 'bytes': len(archive.read(n)), 'sha256': digest(archive.read(n))}
                   for n in sorted(notice_names)]
        supplemental = [notice_pin(p) for p in provenance.get('supplemental_notices', [])]
        if not notices and not supplemental:
            raise ValueError('Wheel needs actual embedded or source-bound supplemental notice text')
        return dict(filename=path.name, sha256=artifact_hash, bytes=path.stat().st_size,
                    name=name, version=version, metadata_path=metadata[0],
                    metadata_sha256=digest(archive.read(metadata[0])), declared_license_metadata=license_fields,
                    embedded_notices=notices, supplemental_notices=supplemental,
                    native_extensions=sorted(n for n in names if n.endswith(('.so', '.pyd'))),
                    **evidence(provenance))


def wheel_inventory(inputs):
    unique = {}
    memberships = []
    selected_locks = {}
    for config in (REPO / 'configs/apps').glob('*.json'):
        app = json.loads(config.read_text())
        if 'runtime_lock' in app:
            selected_locks[app['runtime_lock']] = app['runtime_lock_sha256']
    if {h['lock'] for h in inputs['wheelhouses']} != set(selected_locks) or len(inputs['wheelhouses']) != len(selected_locks):
        raise ValueError('Wheelhouses must exactly cover current application runtime locks')
    for house in inputs['wheelhouses']:
        lock = checked_path(REPO, house['lock'])
        if sha(lock) != house['lock_sha256'] or sha(lock) != selected_locks[house['lock']]:
            raise ValueError('Wheel runtime lock hash mismatch')
        expected = locked_wheels(lock)
        wheels = sorted(Path(house['root']).glob('*.whl'))
        if any(p.is_symlink() or not p.is_file() for p in wheels):
            raise ValueError('Wheelhouse has nonregular wheel inputs')
        if len(wheels) != len(expected) or {sha(p) for p in wheels} != set(expected):
            raise ValueError('Wheelhouse must exactly match selected runtime lock')
        for wheel in wheels:
            hashed = sha(wheel)
            record = inspect_wheel(wheel, expected[hashed], inputs['wheel_sources'][hashed])
            if hashed in unique and unique[hashed] != record:
                raise ValueError('Conflicting wheel identity')
            unique[hashed] = record
        memberships.append({'lock': house['lock'], 'lock_sha256': sha(lock), 'artifacts': sorted(expected)})
    if set(inputs['wheel_sources']) != set(unique):
        raise ValueError('Wheel source provenance must exactly cover selected artifacts')
    return {'artifacts': [unique[k] for k in sorted(unique)], 'runtime_locks': sorted(memberships, key=lambda x: x['lock'])}


def application_license(record, config, source):
    notices = [notice_pin(p) for p in record['notices']]
    status = record.get('license_status', 'source-bound-notice-text-inventoried')
    if status == 'source-bound-notice-text-inventoried' and notices:
        return dict(notices=notices, license_status=status, unresolved_license_declaration=False)
    if status != 'not-declared-in-inspected-source' or notices:
        raise ValueError('Application needs notice text or an explicit unresolved source-license inspection')
    if 'source_artifact' not in record or 'license_inspection' not in record:
        raise ValueError('Unresolved license declaration requires source artifact and inspection receipt pins')
    artifact = file_pin(record['source_artifact'])
    if artifact['sha256'] != source.get('sha256'):
        raise ValueError('License inspection source artifact differs from source identity hash')
    if config.get('source_sha256') and artifact['sha256'] != config['source_sha256']:
        raise ValueError('License inspection source artifact differs from selected application source')
    if isinstance(config.get('source'), str):
        if checked_path(record['source_artifact']['root'], record['source_artifact']['path']).resolve() != checked_path(REPO, config['source']).resolve():
            raise ValueError('License inspection must cover the selected source file')
    inspection = file_pin(record['license_inspection'])
    receipt = json.loads(checked_path(record['license_inspection']['root'], record['license_inspection']['path']).read_text())
    inspected = receipt.get('inspected_paths')
    if (receipt.get('license_status') != status or receipt.get('source_sha256') != artifact['sha256']
            or receipt.get('notices') != [] or not isinstance(inspected, list) or not inspected
            or not all(isinstance(path, str) and path for path in inspected)
            or record['source_artifact']['path'] not in inspected):
        raise ValueError('License inspection receipt does not bind the inspected source and absent declaration')
    return dict(notices=[], license_status=status, unresolved_license_declaration=True,
                source_artifact=artifact, license_inspection=dict(inspection, inspected_paths=inspected),
                inspection_scope='named source and recorded license candidates; no source-license or repository compliance conclusion')


def applications(inputs):
    selected = {str(p.relative_to(REPO)) for p in (REPO / 'configs/apps').glob('*.json')}
    selected.add('configs/host-os/rauc-package.json')
    if set(inputs['applications']) != selected:
        raise ValueError('Applications must exactly cover current selected configs and RAUC')
    records = []
    for name in sorted(selected):
        record = inputs['applications'][name]
        path = checked_path(REPO, name)
        if sha(path) != record['config_sha256']:
            raise ValueError('Application config changed: ' + name)
        c = json.loads(path.read_text())
        version = c.get('package_version', c.get('version'))
        if record['version'] != version:
            raise ValueError('Obsolete application package version')
        source = source_pin(record['source_pin'])
        commit = c.get('source_commit', c.get('source', {}).get('commit') if isinstance(c.get('source'), dict) else None)
        if commit and source.get('commit') != commit:
            raise ValueError('Application source commit mismatch')
        if isinstance(c.get('source'), dict) and source.get('sha256') != c['source']['archive_sha256']:
            raise ValueError('Application source archive mismatch')
        if c.get('source_sha256') and source.get('sha256') != c['source_sha256']:
            raise ValueError('Application source hash mismatch')
        if 'runtime_lock' in c and sha(checked_path(REPO, c['runtime_lock'])) != c['runtime_lock_sha256']:
            raise ValueError('Selected application runtime lock changed')
        patches = [file_pin(dict(p, root=str(REPO))) for p in c.get('source_patches', c.get('patches', []))]
        licensing = application_license(record, c, source)
        records.append(dict(config=name, config_sha256=sha(path), version=version,
                            artifact=file_pin(record['artifact']), patches=patches,
                            **licensing, **evidence(record)))
    return records


def npm_archive_notices(lock_path, package, pin, root):
    """Bind copied notice text to an exact supplier tarball and lock integrity."""
    name = package.get('name', lock_path.rsplit('node_modules/', 1)[-1])
    if (pin['name'], pin['version'], pin['integrity']) != (name, package['version'], package['integrity']):
        raise ValueError('NPM dependency name/version/integrity mismatch')
    records = [pin['archive'], pin['package_json'], *pin['notices']]
    if any(Path(p['root']).resolve() != Path(root).resolve() for p in records):
        raise ValueError('NPM archive and copied texts must use the assigned archive notice root')
    archive_record = file_pin(pin['archive'])
    archive_path = checked_path(root, pin['archive']['path'])
    integrities = {}
    for token in package['integrity'].split():
        algorithm, separator, encoded = token.partition('-')
        if separator and algorithm in ('sha512', 'sha384', 'sha256', 'sha1'):
            try:
                integrities[algorithm] = base64.b64decode(encoded, validate=True)
            except ValueError as error:
                raise ValueError('Malformed NPM supplier integrity') from error
    algorithm = next((a for a in ('sha512', 'sha384', 'sha256', 'sha1') if a in integrities), None)
    if not algorithm:
        raise ValueError('NPM archive needs supported exact supplier integrity')
    hasher = hashlib.new(algorithm)
    with archive_path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            hasher.update(chunk)
    if hasher.digest() != integrities[algorithm]:
        raise ValueError('NPM supplier archive integrity mismatch')
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        if len({m.name for m in members}) != len(members) or any(
                PurePosixPath(m.name).is_absolute() or '..' in PurePosixPath(m.name).parts for m in members):
            raise ValueError('Unsafe or duplicate NPM archive member')
        primary_metadata = [member.name for member in members if member.isfile()
                            and len(PurePosixPath(member.name).parts) == 2
                            and PurePosixPath(member.name).name == 'package.json']
        if len(primary_metadata) != 1 or pin['package_json']['archive_member'] != primary_metadata[0]:
            raise ValueError('Require the unique primary package.json under one archive top-level directory')
        recognized = {member.name for member in members if not member.isdir()
                      and NOTICE.match(PurePosixPath(member.name).name)}
        supplied = [text_pin['archive_member'] for text_pin in pin['notices']]
        if len(set(supplied)) != len(supplied) or not recognized.issubset(supplied):
            raise ValueError('NPM inventory must not omit recognizable embedded notices')
        def bound_text(text_pin):
            record = file_pin(text_pin)
            member = archive.getmember(text_pin['archive_member'])
            if not member.isfile():
                raise ValueError('NPM notice/package metadata must be regular archive text')
            content = archive.extractfile(member).read()
            if digest(content) != record['sha256']:
                raise ValueError('Copied NPM notice/package metadata differs from supplier archive')
            return dict(record, archive_member=member.name), content
        metadata_record, metadata = bound_text(pin['package_json'])
        metadata = json.loads(metadata)
        if (metadata['name'], metadata['version']) != (name, package['version']):
            raise ValueError('NPM archive package metadata identity mismatch')
        declared_license = metadata.get('license')
        if 'declared_license' in pin and pin['declared_license'] != declared_license:
            raise ValueError('Copied NPM declaration differs from verified package metadata')
        if not pin['notices'] and not (isinstance(declared_license, str) and declared_license.strip()
                                      or isinstance(declared_license, dict) and declared_license):
            raise ValueError('NPM archive without notice text needs a nonempty supplier license declaration')
        notices = [bound_text(text_pin)[0] for text_pin in pin['notices']]
        classification = ('supplier-archive-and-license-text-verified-no-project-source-build-claim'
                          if notices else 'supplier-declaration-only; no embedded notice text')
    return dict(archive=archive_record, package_json=metadata_record, notices=notices,
                integrity_algorithm_verified=algorithm, name=name,
                archive_declared_license=declared_license,
                archive_declared_license_sha256=digest((declared_license if isinstance(declared_license, str)
                                                       else serialize(declared_license)).encode()),
                archive_declared_license_hash_encoding=('utf8' if isinstance(declared_license, str)
                                                        else 'canonical-json-utf8-with-terminal-newline'),
                recognizable_notice_file_count=len(recognized),
                classification=classification)


def npm_supplemental(pin, texts, package, archive_path=None):
    if not pin: return []
    from resolve_npm_notices import validate_record
    record = validate_record(pin, texts['name'], package['version'], package['integrity'], texts['archive']['sha256'], archive_path)
    return [dict(url=p['url'], sha256=p['sha256'], bytes=len(p['text'].encode('utf-8')),
                 source_revision=record['source_revision'], source_repository=record['source_repository'],source_mapping=record['source_mapping'])
            for p in record['notices']]


def npm_inventory(pin):
    record = file_pin(pin)
    selected = json.loads((REPO / 'configs/apps/mainsail.json').read_text())
    if record['sha256'] != selected['patched_package_lock_sha256']:
        raise ValueError('NPM inventory requires the selected patched Mainsail lock')
    lock = json.loads(checked_path(pin['root'], pin['path']).read_text())
    if set(pin['dependency_notices']) != set(lock['packages']) - {''}:
        raise ValueError('NPM source notices must exactly cover all selected production/build dependencies')
    supplements = {}
    if pin.get('supplemental_notices'):
        supplemental_pin = pin['supplemental_notices']
        file_pin(supplemental_pin)
        supplemental = json.loads(checked_path(supplemental_pin['root'], supplemental_pin['path']).read_text())
        for item in supplemental['records']:
            if item['path'] in supplements: raise ValueError('Duplicate supplemental dependency')
            supplements[item['path']] = item
        if set(supplements) - set(lock['packages']): raise ValueError('Extraneous supplemental dependency')
    packages = []
    for path, package in sorted(lock['packages'].items()):
        if not path:
            continue
        if not package.get('version') or not package.get('integrity') or not package.get('resolved'):
            raise ValueError('NPM dependency lacks exact version/integrity/supplier reference')
        texts = npm_archive_notices(path, package, pin['dependency_notices'][path], pin['archive_notice_root'])
        texts['supplemental_notices'] = npm_supplemental(supplements.get(path), texts, package,
            checked_path(pin['archive_notice_root'],pin['dependency_notices'][path]['archive']['path']))
        if texts['supplemental_notices'] and not texts['notices']:
            texts['classification'] = 'supplier-declaration-and-exact-version-upstream-supplemental-text'
        packages.append(dict(path=path, version=package['version'], integrity=package['integrity'],
                             supplier_url=package['resolved'], declared_license=package.get('license'),
                             dependency_scope='build' if package.get('dev') else 'production',
                             optional=bool(package.get('optional')), **texts))
    return dict(lock=record, packages=packages,
                notice_coverage=dict(inspected_supplier_archives=len(packages),
                                     dependencies_with_notice_text=sum(bool(p['notices'] or p['supplemental_notices']) for p in packages),
                                     declaration_only_dependencies=sum(not (p['notices'] or p['supplemental_notices']) for p in packages)))


def debian_inventory(root):
    inputs = {name: REPO / ('configs/host-os/recovery-' + name + '.json')
              for name in ('packages', 'sources', 'copyrights', 'license-references')}
    packages, sources, copyrights, references = [json.loads(inputs[name].read_text())
                                                for name in ('packages', 'sources', 'copyrights', 'license-references')]
    mappings = {}
    for source in sources['sources']:
        for binary in source['binaries']:
            if binary['package'] in mappings:
                raise ValueError('Duplicate Debian source mapping')
            mappings[binary['package']] = (source, binary)
    selected = {p['package'] for p in packages['packages']}
    if selected != set(copyrights) or selected != set(mappings):
        raise ValueError('Incomplete Debian copyright/source closure')
    refs = {(r['package'], r['raw_token']): r for r in references['entries']}
    records = []
    for package in sorted(packages['packages'], key=lambda p: p['package']):
        name = package['package']
        source, binary = mappings[name]
        if any(package[key] != binary[key] for key in ('version', 'architecture', 'sha256')) or any(
                package[key] != source[key] for key in ('source', 'source_version')):
            raise ValueError('Debian binary/source/version mismatch')
        copyright = copyrights[name]
        actual = checked_path(root, copyright['path'])
        if sha(actual) != copyright['sha256'] or actual.resolve() != checked_path(root, copyright['resolved_path']).resolve():
            raise ValueError('Debian copyright hash/link mismatch')
        common = []
        for token, hashed in sorted(copyright['common_license_references'].items()):
            if HASH.fullmatch(hashed):
                target = 'usr/share/common-licenses/' + token
                if sha(checked_path(root, target)) != hashed:
                    raise ValueError('Common license hash mismatch')
                common.append(dict(raw_token=token, target=target, sha256=hashed, classification='shipped-text'))
            else:
                ref = refs.get((name, token))
                if not ref or ref['copyright_sha256'] != sha(actual):
                    raise ValueError('Missing supplier-reference review')
                target = ref['candidate_target']
                if ref['target_exists']:
                    if sha(checked_path(root, target)) != ref['target_sha256']:
                        raise ValueError('Reviewed common license hash mismatch')
                elif (Path(root) / target).exists():
                    raise ValueError('Historical missing supplier target changed')
                common.append(dict(raw_token=token, target=target, sha256=ref.get('target_sha256'),
                                   classification=ref['classification'], target_exists=ref['target_exists'],
                                   exact_occurrences=ref['exact_occurrences']))
        records.append(dict(package=name, version=package['version'], architecture=package['architecture'],
                            artifact_sha256=package['sha256'], source=source['source'],
                            source_version=source['source_version'], source_archives=source['source_archives'],
                            source_index=source['source_index'], classification='upstream-debian-binary',
                            source_build_proven=False, copyright=dict(path=copyright['path'], sha256=sha(actual)),
                            common_license_references=common))
    return dict(input_hashes={name: sha(path) for name, path in sorted(inputs.items())},
                snapshot=packages['snapshot'], packages=records,
                source_availability='authenticated-index-mapping; archives are not asserted retrieved or rebuilt')


def generate(inputs):
    tools = []
    for tool in inputs['build_tools']:
        notices = [notice_pin(p) for p in tool['notices']]
        if not notices:
            raise ValueError('Build tool needs actual source-bound license text')
        tools.append(dict(name=tool['name'], version=tool['version'], artifact=file_pin(tool['artifact']),
                          notices=notices, **evidence(tool)))
    return dict(format_version=1, scope='selected-software-and-documented-OS-license-inventory',
                legal_compliance_assessed=False, hardware_release_qualified=False,
                applications=applications(inputs), wheels=wheel_inventory(inputs),
                mainsail_dependencies=npm_inventory(inputs['mainsail']),
                debian=debian_inventory(inputs['debian_root']),
                build_tools=sorted(tools, key=lambda x: (x['name'], x['version'])))


def serialize(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = serialize(generate(json.loads(args.inputs.read_text())))
    args.output.write_text(result)
    print(json.dumps({'output_sha256': digest(result.encode()), 'bytes': len(result.encode())}))


if __name__ == '__main__':
    main()
