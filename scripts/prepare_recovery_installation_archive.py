#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prepare a private derived installation archive; never install or activate it.

Run on the development host in the existing private mount-namespace wrapper.
The normal image is inspected using kernel-verified read-only mounts; no image
code is executed. Original data and old generations remain unchanged. Failed
workspaces are retained for diagnosis. Archives contain private owner data.

Unit callers can inject an image reader; the CLI always uses actual image bytes.
This is offline preparation evidence, not hardware or release qualification.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_export import Export, identity, inventory, opened
from sv08_restore import Restore, pinned_archive, require
from sv08_state import Store, atomic_json, snapshot, fsync_dir
from sv08_recovery_activation import compatible, validate_boot
from sv08_printer_firmware import read_regular, validate_assignment


def digest_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    checksum = hashlib.sha256()
    while block := os.read(fd, 1024 * 1024): checksum.update(block)
    return checksum.hexdigest()


def checked_hash(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'Invalid SHA256 binding')
    return value


@contextmanager
def pinned_file(path, expected):
    """Hold a regular file, checking both digest and pathname again on exit."""
    checked_hash(expected)
    with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
        stamp = identity(os.fstat(fd))
        require(stat.S_ISREG(stamp[2]) and stamp[8] == 1, 'Expected single-link regular input')
        require(digest_fd(fd) == expected, 'Input SHA256 differs')
        yield fd
        require(identity(os.fstat(fd)) == stamp and digest_fd(fd) == expected, 'Input changed')
        with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as now:
            require(identity(os.fstat(now)) == stamp, 'Input pathname changed')


class Workspace:
    """Local private-directory admission, with no claim about removable media."""
    def __init__(self, path):
        self.path = Path(path)
        with opened(self.path) as fd: self.stamp = identity(os.fstat(fd))[:2]
        self.fingerprint = list(self.stamp)
        self.recheck()

    def recheck(self):
        with opened(self.path) as fd:
            st = os.fstat(fd)
            require(identity(st)[:2] == self.stamp and st.st_uid == os.geteuid() and
                    stat.S_IMODE(st.st_mode) == 0o700, 'Private workspace changed')

    @contextmanager
    def admission(self, unused):
        self.recheck()
        yield self
        self.recheck()


def restore(archive, destination, workspace):
    operation = Restore({'archive': dict(path=archive)},
                        {'local': dict(root=str(destination))}, workspace.admission)
    operation.execute(operation.prepare('local', 'archive'))


def image_manifest(image, scratch, artifact):
    """Read normal A from the composed supported image, never data."""
    from image_license_inventory import geometry, mounted_image, safe_file, file_hash
    parts = geometry(image)
    require(parts == artifact['geometry']['partition_records'] and
            image.stat().st_size == artifact['image_bytes'], 'Actual image geometry differs from receipt')
    selected = [p for p in parts if p.get('name') == 'root-a']
    require(len(selected) == 1, 'Exactly one normal A image filesystem required')
    part = selected[0]
    root_record = artifact['partition_images']['root-a']
    require(root_record['bytes'] == part['size_bytes'] and
            file_hash(image, part['offset_bytes'], part['size_bytes']) == root_record['sha256'],
            'Actual normal A partition differs from receipt')
    with mounted_image(image, part, scratch) as root:
        path = safe_file(root, 'usr/lib/sv08/release.json')
        return read_regular(path)


def settled_operations(data, store):
    """Known historical terminal journals survive; unknown/interrupted ones fail."""
    from sv08_transaction import Transaction
    tx = Transaction(store, None, None).load()
    require(tx is None or tx['phase'] in ('complete', 'cancelled', 'failed'), 'Unfinished update operation')
    for path in data.rglob('.sv08-activation*'):
        require(path.is_file() and not path.is_symlink() and path.suffix == '.json',
                'Unfinished or unknown activation operation')
        value = json.loads(path.read_bytes())
        require(value.get('format_version') == 1 and value.get('phase') in ('committed', 'rolled-back'),
                'Unfinished or unknown activation journal')
    history = store.root/'customizations'
    if history.exists():
        for path in history.iterdir():
            require(path.is_file() and not path.is_symlink() and path.suffix == '.json', 'Unknown package operation')
            value = json.loads(path.read_bytes())
            require(value.get('status') in ('completed', 'failed') and type(value.get('exit_status')) is int,
                    'Unfinished package operation')


def copy_metadata(source, target):
    """SQLite backup replaces its inode; restore source ownership/mode explicitly."""
    for original in [source, *source.rglob('*')]:
        copied = target/original.relative_to(source)
        if not copied.exists(): continue  # WAL/SHM intentionally recovered by snapshot.
        info = original.lstat()
        require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode), 'Unsupported generation node')
        actual = copied.stat()
        if (actual.st_uid, actual.st_gid) != (info.st_uid, info.st_gid):
            os.chown(copied, info.st_uid, info.st_gid)
        os.chmod(copied, stat.S_IMODE(info.st_mode))
        actual = copied.stat()
        require((actual.st_uid, actual.st_gid, stat.S_IMODE(actual.st_mode)) ==
                (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)), 'Cannot preserve generation metadata')


def contents(root):
    """Export-representable metadata/bytes, independent of inode or ns timestamps."""
    result = []
    for relative, stamp in inventory(root):
        path = root.joinpath(*relative)
        if stat.S_ISREG(stamp[2]):
            with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW) as fd: payload = digest_fd(fd)
        elif stat.S_ISLNK(stamp[2]): payload = stamp[9]
        else: payload = None
        result.append((relative, stat.S_IMODE(stamp[2]), stamp[6], stamp[7], stamp[4]//10**9, payload))
    return result


def retained_system(root):
    """Owner identity and shared data, excluding only active start permission."""
    return [row for row in contents(root) if row[0][0] in ('system', 'shared') and
            row[0] != ('system', 'klipper-start.json')]


def prepare(*, archive, archive_sha256, source, image, image_sha256, receipt,
            receipt_sha256, source_revision, workspace, reader=image_manifest):
    """All writes are beneath one new private workspace. Inputs stay pinned."""
    archive, image, receipt, workspace = map(lambda p: Path(p).absolute(), (archive, image, receipt, workspace))
    validate_boot({k: source[k] for k in ('slot', 'release', 'state_schema', 'release_revision')})
    from sv08_state import identifier
    identifier(source['generation'])
    require(set(source) == {'slot','release','state_schema','release_revision','generation'}, 'Invalid source binding')
    require(isinstance(source_revision, str) and re.fullmatch('[0-9a-f]{40}', source_revision), 'Invalid source revision')
    require(all(not p.is_relative_to(workspace) and not workspace.is_relative_to(p)
                for p in (archive, image, receipt)), 'Inputs and workspace overlap')
    # Refuse symlink ancestors before mkdir. Never reuse or clean failed work.
    with opened(workspace.parent): pass
    workspace.mkdir(mode=0o700)
    local = Workspace(workspace)
    with pinned_archive(archive) as (archive_fd, archive_stamp), \
            pinned_file(image, image_sha256), pinned_file(receipt, receipt_sha256) as receipt_fd:
        require(digest_fd(archive_fd) == checked_hash(archive_sha256), 'Archive SHA256 differs')
        os.lseek(receipt_fd, 0, os.SEEK_SET)
        require(os.fstat(receipt_fd).st_size <= 16*1024**2, 'Artifact receipt exceeds bound')
        artifact = json.loads(os.read(receipt_fd, 16*1024**2))
        manifest = reader(image, workspace, artifact)
        target = dict(slot='A', release=manifest['release'], state_schema=manifest['state_schema'],
                      release_revision=manifest['release_revision'])
        validate_boot(target)
        validate_artifact(artifact, manifest, image_sha256, source_revision)
        assignment = validate_assignment(manifest['mcu_firmware'], target['release'])
        require(assignment['host_klipper_commit'] == manifest['klipper_commit'],
                'MCU assignment differs from pinned normal host')
        data = workspace/'derived-data'
        restore(archive, data, local)
        store = Store(data/'sv08')
        source_boot = {key: source[key] for key in target}
        state = compatible(store.root, source_boot, False)
        require(state['requested_mode'] == 'immutable' and all(not r['customized'] for r in state['slots'].values()),
                'Writable or customized OS state cannot seed an installation')
        record = state['slots'][source['slot']]
        require(record['generation'] == source['generation'], 'Source generation differs')
        settled_operations(data, store)
        registry = (store.root/'state.json').read_bytes()
        old_generation = store.generation_path(record)
        old_inventory = inventory(store.root/'generations')
        old_contents = contents(store.root/'generations')
        retained = retained_system(store.root)
        backup = store.root/('installation-preparation-'+uuid.uuid4().hex)
        backup.mkdir(mode=0o700)
        (backup/'original-state.json').write_bytes(registry)
        os.chmod(backup/'original-state.json', 0o600)
        permission = store.root/'system/klipper-start.json'
        quarantined = permission.exists()
        if quarantined:
            require(permission.is_file() and not permission.is_symlink(), 'Invalid physical-start permission')
            parent_stamp = permission.parent.stat()
            os.rename(permission, backup/'klipper-start.json')
            # Moving a child necessarily changes its directory's mtime. Retain
            # that original metadata too; the permission itself stays quarantined.
            os.utime(permission.parent, ns=(parent_stamp.st_atime_ns, parent_stamp.st_mtime_ns))
        generation = 'installation-'+uuid.uuid4().hex
        new_generation = store.root/'generations'/generation
        with store.locked(), store.budget.locked():
            store.check_copy_budget(record)
            snapshot(old_generation, new_generation)
            copy_metadata(old_generation, new_generation)
            recommendation = new_generation/'mcu-firmware.json'
            recommendation.unlink(missing_ok=True)
            atomic_json(recommendation, assignment)
            # Existing slot records survive verbatim in original-state.json. B is
            # retained in the seed; A alone is explicitly assigned for installation.
            state['slots']['A'] = dict(release=target['release'], schema=target['state_schema'],
                                      release_revision=target['release_revision'], generation=generation,
                                      parent_generation=source['generation'], customized=False)
            store.save(state)
        require([entry for entry in inventory(store.root/'generations') if entry[0][0] != generation] == old_inventory,
                'Original generations changed')
        require([row for row in contents(store.root/'generations') if row[0][0] != generation] == old_contents,
                'Original generation bytes or metadata changed')
        require(retained_system(store.root) == retained, 'Retained identity or shared data changed')
        require((backup/'original-state.json').read_bytes() == registry and not permission.exists(),
                'Registry or commissioning quarantine failed')
        compatible(store.root, target, False)
        out = workspace/'unpublished'; out.mkdir(mode=0o700)
        exporter = Export(data, {'local': dict(path=out)}, local.admission)
        result = exporter.execute(exporter.prepare('local'))
        derived = out/result['filename']
        restore(derived, workspace/'roundtrip', local)
        roundtrip = workspace/'roundtrip/sv08'
        compatible(roundtrip, target, False)
        require([row for row in contents(roundtrip/'generations') if row[0][0] != generation] == old_contents,
                'Roundtrip original generation bytes or metadata changed')
        require(retained_system(roundtrip) == retained, 'Roundtrip retained identity or shared data changed')
        require(contents(data) == contents(workspace/'roundtrip'), 'Roundtrip metadata or contents differ')
        require(not (roundtrip/'system/klipper-start.json').exists(), 'Inherited commissioning remains active')
        require(identity(os.fstat(archive_fd)) == archive_stamp and digest_fd(archive_fd) == archive_sha256,
                'Original archive changed before publication')
        with pinned_archive(archive) as (current, stamp):
            require(stamp == archive_stamp and digest_fd(current) == archive_sha256, 'Original archive pathname changed')
        receipt_value = dict(format_version=1, kind='derived-installation-archive',
            evidence_class='offline-preparation-with-restore-roundtrip', source=source,
            target=dict(target, generation=generation, parent_generation=source['generation']),
            source_revision=source_revision, input_archive_sha256=archive_sha256,
            image_sha256=image_sha256, artifact_receipt_sha256=receipt_sha256,
            output_archive_sha256=result['sha256'], original_registry_sha256=hashlib.sha256(registry).hexdigest(),
            original_generations_preserved=True, original_registry_preserved=True,
            physical_start_quarantined=quarantined, fresh_commissioning_required=True,
            limitations=['No installation, activation, OS health, hardware or release qualification.',
                         'Archive includes private owner data; keep original and derived archives private.'])
        # No successful output name or receipt is published until every invariant.
        # Leaving an unpublished export after a failure preserves diagnostic work.
    final = workspace/'installation.tar'
    os.rename(derived, final)
    atomic_json(workspace/'receipt.json', receipt_value)
    fsync_dir(workspace)
    return dict(archive=str(final), receipt=str(workspace/'receipt.json'), sha256=result['sha256'])


def validate_artifact(artifact, manifest, image_sha256, source_revision):
    """Validate the pinned supported assembler receipt and actual embedded manifest."""
    require(artifact.get('status') == 'supported-candidate-awaiting-qualification' and
            artifact.get('image_sha256') == image_sha256 and
            artifact.get('profile', {}).get('project_source_revision') == source_revision and
            manifest.get('project_source_revision') == source_revision,
            'Artifact image/source receipt differs')
    profile = artifact['profile']
    require(profile.get('purpose') == 'supported-configured-printer-candidate' and
            manifest.get('state_schema') == 1 and
            all(profile.get(key) == manifest.get(key) for key in
                ('release','release_revision','hardware_profile','klipper_commit')),
            'Artifact release receipt differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive','image','receipt','workspace'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('archive-sha256','image-sha256','receipt-sha256','source-revision','source-release','source-generation'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--source-slot', choices=('A','B'), required=True)
    parser.add_argument('--source-schema', type=int, required=True)
    parser.add_argument('--source-release-revision', type=int, required=True)
    args = parser.parse_args()
    require(os.stat('/proc/self/ns/mnt').st_ino != os.stat('/proc/1/ns/mnt').st_ino,
            'Use the existing private mount-namespace wrapper')
    source = dict(slot=args.source_slot, release=args.source_release, generation=args.source_generation,
                  state_schema=args.source_schema, release_revision=args.source_release_revision)
    print(json.dumps(prepare(archive=args.archive, archive_sha256=args.archive_sha256, source=source,
        image=args.image, image_sha256=args.image_sha256, receipt=args.receipt, receipt_sha256=args.receipt_sha256,
        source_revision=args.source_revision, workspace=args.workspace)))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError) as error: sys.exit(str(error))
