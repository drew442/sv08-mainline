#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prepare deterministic exact-artifact evidence packages, without publishing.

Fixed profiles execute real image/source/inventory checks. No caller receipt or
release-ready assertion is accepted. Both profiles leave hardware, third-party
corresponding-source completeness and overall release qualification unestablished.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import subprocess
from pathlib import PurePosixPath
import tempfile
from image_license_inventory import encoded, file_hash, inspect_artifact
import license_inventory

PROFILES = {'project-source': ('image','public-project-source'),
            'selected-software': ('image','public-project-source','selected-software-notices')}


def required_application_partitions(roots):
    """Use actual partition roles to require both normal roots on A/B disks."""
    selected=[root['selected_partition'] for root in roots]
    if any(type(number) is not int or number<0 for number in selected) or len(set(selected))!=len(selected):
        raise ValueError('Invalid or duplicate software root partition identity')
    tables=[root.get('partitions') for root in roots]
    if not any(table is not None for table in tables):
        if len(roots)>1:raise ValueError('Missing partition identities for multiple software roots')
        return set()  # Legacy single-root inventory; exact payload must still match.
    identities=[]
    for table in tables:
        if not isinstance(table,list) or not table:raise ValueError('Missing software root partition table')
        numbers=set();names=set();identity={}
        for part in table:
            number=part['number'];name=part.get('name','')
            if (type(number) is not int or number<0 or number in numbers or
                    not isinstance(name,str) or (name and name in names)):
                raise ValueError('Invalid or duplicate partition role/number identity')
            numbers.add(number)
            if name:names.add(name)
            identity[number]=name
        identities.append(identity)
    table=identities[0]
    if any(identity!=table for identity in identities):raise ValueError('Contradictory software root partition identities')
    if not set(selected)<=set(table):raise ValueError('Software root partition is absent from table')
    roles={name:number for number,name in table.items() if name in ('root-a','root-b')}
    ab_evidence=any(name in ('root-b','boot-b','recovery') for name in table.values())
    if not roles and not ab_evidence:return set()  # Raw/DOS or generic single-root geometry.
    if set(roles)=={'root-a'} and not ab_evidence and selected==[roles['root-a']]:return set()
    if set(roles)!={'root-a','root-b'}:raise ValueError('Incomplete normal A/B partition roles')
    required=set(roles.values())
    if not required<=set(selected):raise ValueError('Missing normal-root inventory for A/B disk')
    return required


def installed_application_bindings(inputs, roots):
    """Compare .deb identity and installed usr/opt software, without installing it."""
    required=required_application_partitions(roots)
    bindings=[]
    for config,record in sorted(inputs['applications'].items()):
        pin=record['artifact'];license_inventory.file_pin(pin)
        artifact=license_inventory.checked_path(pin['root'],pin['path'])
        if artifact.suffix != '.deb': raise ValueError('Unsupported installed application artifact format')
        identity=subprocess.check_output(['dpkg-deb','--show','--showformat=${Package}\t${Version}\t${Architecture}',str(artifact)],
            text=True,timeout=30).split('\t')
        if len(identity)!=3: raise ValueError('Invalid Debian application identity')
        payload={}; total=0; excluded=0; non_usr=0
        with subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(artifact)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as process:
            try:
                with tarfile.open(fileobj=process.stdout,mode='r|') as archive:
                    for member in archive:
                        name=member.name.removeprefix('./');relative=PurePosixPath(name)
                        if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe application payload path')
                        if member.isdir(): continue
                        if not name.startswith('usr/'): non_usr+=1
                        if not name.startswith(('usr/', 'opt/sv08-mainline/')):
                            excluded+=1;continue
                        if name in payload: raise ValueError('Duplicate application payload path')
                        if member.isfile():
                            total+=member.size
                            if total>1024*1024*1024: raise ValueError('Application payload inventory exceeds bound')
                            stream=archive.extractfile(member);hasher=hashlib.sha256()
                            for chunk in iter(lambda:stream.read(1024*1024),b''):hasher.update(chunk)
                            payload[name]=dict(kind='file',sha256=hasher.hexdigest())
                        elif member.issym():payload[name]=dict(kind='symlink',target=member.linkname)
                        else: raise ValueError('Unsupported application payload member')
                if process.wait(timeout=30)!=0: raise ValueError('Cannot read application Debian payload')
            except BaseException:
                process.kill();process.wait();raise
        if not payload: raise ValueError('Application artifact lacks supported software payload')
        matched=[]
        for root in roots:
            packages={(p['name'],p['version'],p['architecture']) for p in root['packages']}
            files={f['path']:f for f in root['files']}
            if tuple(identity) in packages and all(name in files and all(files[name].get(k)==v for k,v in expected.items())
                    for name,expected in payload.items()): matched.append(root['selected_partition'])
        if not matched or not required<=set(matched):
            raise ValueError('Application package identity/payload not found in every required normal slot of actual image: '+config)
        bindings.append(dict(config=config,package=identity[0],version=identity[1],architecture=identity[2],
            artifact_sha256=pin['sha256'],
            software_payload_files=len(payload),
            usr_payload_files=sum(name.startswith('usr/') for name in payload),
            opt_payload_files=sum(name.startswith('opt/sv08-mainline/') for name in payload),
            matching_partitions=matched,required_normal_partitions=sorted(required),
            excluded_non_software_members=excluded,
            # Legacy count remains literally non-usr, including supported opt.
            excluded_non_usr_members=non_usr))
    return bindings


def prepare(image, public_source, profile='selected-software', inventory_inputs=None, scratch=None):
    if profile not in PROFILES: raise ValueError('Unknown release preparation profile')
    if profile=='selected-software' and inventory_inputs is None:
        raise ValueError('Selected software profile requires inventory inputs')
    if profile=='project-source' and inventory_inputs is not None:
        raise ValueError('Inventory inputs require selected-software profile')
    public_raw=Path(public_source).read_bytes(); public=json.loads(public_raw)
    input_raw=Path(inventory_inputs).read_bytes() if inventory_inputs else None
    # Invokes the existing anonymous public source qualifier inside each mounted
    # actual root, not a stored success receipt or a staging directory.
    image_record=inspect_artifact(image,scratch,public)
    roots=image_record['roots']
    if not roots or any(not r.get('source_qualification',{}).get('qualified') for r in roots):
        raise ValueError('Every software root must pass actual public project source qualification')
    revisions={r['source_qualification']['source_revision'] for r in roots}
    if revisions != {public['source_revision']}: raise ValueError('Artifact source revisions disagree')
    inventory=None; application_bindings=[]
    if input_raw is not None:
        if any(not root['packages'] for root in roots):
            raise ValueError('Selected software profile requires actual installed package databases in every software root')
        inputs=json.loads(input_raw)
        inventory=license_inventory.generate(inputs)
        application_bindings=installed_application_bindings(inputs,roots)
        if inventory['mainsail_dependencies']['notice_coverage']['declaration_only_dependencies']:
            raise ValueError('Unresolved NPM supplemental notice coverage')
        if any(a.get('unresolved_license_declaration') for a in inventory['applications']):
            raise ValueError('Unresolved application license declaration')
        # Each current input configuration must belong to the actual installed
        # source archive; stale current checkout configuration cannot qualify it.
        for root in roots:
            sources=root['project']['source_files']
            for relative in sorted(inputs['applications']):
                path=license_inventory.REPO/relative
                if sources.get(relative) != file_hash(path):
                    raise ValueError('Selected software configuration differs from image source: '+relative)
    if Path(public_source).read_bytes() != public_raw or (inventory_inputs and Path(inventory_inputs).read_bytes()!=input_raw):
        raise ValueError('Release inputs changed during checks')
    if file_hash(image) != image_record['image']['sha256']: raise ValueError('Artifact changed during release checks')
    outputs={'image-inventory.json':encoded(image_record),'public-source.json':encoded(public)}
    if inventory is not None:
        outputs['software-inventory.json']=encoded(inventory)
        outputs['installed-application-bindings.json']=encoded(application_bindings)
    if input_raw:
        inputs=json.loads(input_raw); pin=inputs['mainsail'].get('supplemental_notices')
        if pin:
            license_inventory.file_pin(pin)
            raw=license_inventory.checked_path(pin['root'],pin['path']).read_bytes()
            outputs['npm-supplemental-notices.json']=raw
            from resolve_npm_notices import notice_text
            outputs['npm-notices.txt']=notice_text(json.loads(raw)).encode('utf-8')
    if input_raw and inputs['mainsail'].get('standard_license_texts'):
        pin=inputs['mainsail']['standard_license_texts']
        license_inventory.file_pin(pin)
        raw=license_inventory.checked_path(pin['root'],pin['path']).read_bytes()
        # Recheck immutable source/text anchors after inventory qualification and
        # bind the exported bytes to the records that actually qualified.
        lock_pin=inputs['mainsail']
        lock=json.loads(license_inventory.checked_path(lock_pin['root'],lock_pin['path']).read_bytes())
        standards=license_inventory.npm_standard_license_texts(pin,lock)
        qualified={p['path']:p['standard_license_texts'] for p in inventory['mainsail_dependencies']['packages']
                   if p.get('standard_license_texts')}
        if set(qualified)!=set(standards):
            raise ValueError('Exported standard terms differ from qualified inventory')
        for path,standard in standards.items():
            expected=dict(standard,historical_embedded_notice_absent=True,author_attribution_invented=False)
            if qualified[path]!=[expected]:
                raise ValueError('Exported standard terms differ from qualified inventory')
            text=standard['license_text']
            content=license_inventory.checked_path(license_inventory.REPO,text['path']).read_bytes()
            if license_inventory.digest(content)!=text['sha256']:
                raise ValueError('Standard license text changed before export')
            outputs[Path(text['path']).name]=content
        if license_inventory.digest(raw)!=pin['sha256']:
            raise ValueError('Standard license provenance changed before export')
        outputs['npm-standard-license-texts.json']=raw
    report=dict(format_version=1,profile=profile,checks=[dict(id=name,status='passed') for name in PROFILES[profile]],
        project_source_qualified=True,software_notice_inventory_checked=inventory is not None,
        hardware_qualified=False,overall_release_qualified=False,
        limitations=['Hardware, recovery execution, legal compliance and full reproducibility are not qualified.',
                    'Third-party corresponding-source completeness and opaque boot/data license coverage remain separate.',
                    'Artifact must travel alongside this evidence package and match its exact hash.'])
    outputs['report.json']=encoded(report)
    manifest=dict(format_version=1,scope='release-preparation-evidence',profile=profile,
        artifact=image_record['image'],source_revision=public['source_revision'],
        public_source_input_sha256=hashlib.sha256(public_raw).hexdigest(),
        inventory_input_sha256=hashlib.sha256(input_raw).hexdigest() if input_raw else None,
        files={name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(outputs.items())},
        overall_release_qualified=False)
    outputs['release-manifest.json']=encoded(manifest)
    return outputs


def write_package(output, files):
    output=Path(output)
    if output.exists() or output.is_symlink(): raise ValueError('Package output must not exist')
    with tempfile.TemporaryDirectory(prefix='.release-',dir=output.parent) as temporary:
        staging=Path(temporary)/'package';staging.mkdir()
        for name,raw in sorted(files.items()):
            path=staging/name;path.write_bytes(raw);path.chmod(0o644)
        # A same-parent rename publishes complete files only after all checks pass.
        staging.rename(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True);parser.add_argument('--public-source',required=True)
    parser.add_argument('--profile',choices=tuple(PROFILES),default='selected-software')
    parser.add_argument('--inventory-inputs');parser.add_argument('--scratch');parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:
        if Path(args.output).exists() or Path(args.output).is_symlink(): raise ValueError('Package output must not exist')
        result=prepare(args.image,args.public_source,args.profile,args.inventory_inputs,args.scratch)
        write_package(args.output,result)
        print(result['report.json'].decode(),end='')
    except Exception as error:
        parser.exit(1,'Release preparation refused: '+str(error)+'\n')

if __name__=='__main__': main()
