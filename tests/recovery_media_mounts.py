#!/usr/bin/env python3
"""Real GTK/provider/filesystem fixture; only explicitly created loop images.

Run sudo unshare --mount --pid --fork --propagation private
    /usr/bin/python3 tests/recovery_media_mounts.py
    --work build/recovery-media-new --execute
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import time
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'runtime'))
import sv08_export
from sv08_recovery_media import (Kernel, MediaLease, MediaProvider, PROTOCOL,
                                 WRITER_MODEL, durable_identity, fingerprint)


def run(*args):
    return subprocess.check_output([str(a) for a in args], text=True).strip()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def refused(operation, phrase):
    try:
        operation()
    except (ValueError, OSError) as error:
        assert phrase in str(error), str(error)
        return
    raise AssertionError('Expected refusal: '+phrase)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    work = args.work.resolve()
    if not work.is_relative_to(REPO / 'build') or work.exists():
        parser.error('Use a fresh disposable directory under this checkout build/')
    if not args.execute:
        print(json.dumps(dict(execute=False, work=str(work))))
        return
    if shutil.disk_usage(work.parent).free < 352*1024**2:
        parser.error('Fixture needs 352 MiB free space for five disposable images and reserve')
    if os.getpid() == 1:
        if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
            parser.error('Launch with separate mount/PID namespaces and the inherited proc tree')
        # Discard the inherited proc tree in THIS private namespace, including
        # hidden overmounts, before exposing this disposable PID namespace.
        run('umount', '-l', '/proc')
        run('mount', '-t', 'proc', '-o', 'nosuid,nodev,noexec', 'proc', '/proc')
    else:
        command = Path('/proc/1/cmdline').read_bytes().split(b'\0')
        if len(command) < 2 or Path(os.fsdecode(command[1])).resolve() != Path(__file__).resolve():
            parser.error('The disposable fixture launcher must be PID 1; use documented unshare command')
    if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') != os.readlink('/proc/1/ns/mnt'):
        parser.error('Use private mount AND PID namespaces, mounted proc and Xvfb as documented')
    # A separate PID namespace makes its complete process table inspectable.
    assert int(Path('/proc/1/status').read_text().split('NSpid:')[1].splitlines()[0].split()[0]) == 1
    if not os.environ.get('DISPLAY'):
        # Keep a real PID 1 while xvfb-run waits for its server-ready signal.
        subprocess.run(['xvfb-run', '-a', '/usr/bin/python3', str(Path(__file__).resolve()),
                        '--work', str(work), '--execute'], check=True, timeout=240)
        return
    work.mkdir(mode=0o700)
    (work / 'run').mkdir(mode=0o700)
    for directory in ('recovery', 'source', 'fat', 'writer', 'alias'):
        (work / directory).mkdir()
    seeds = work / 'seeds'
    (seeds / 'recovery/etc/sv08').mkdir(parents=True)
    manifest = b'{"kind":"explicit-disposable-recovery-image","hardware":false}\n'
    (seeds / 'recovery/etc/sv08/recovery-image.json').write_bytes(manifest)
    (seeds / 'source/sv08').mkdir(parents=True)
    (seeds / 'source/sv08/state.json').write_text('damaged registry remains exportable')
    (seeds / 'source/printer.cfg').write_text('private fixture configuration')
    for name in ('recovery', 'source', 'fat', 'writer'):
        with (work / (name+'.img')).open('xb') as stream:
            stream.truncate(64*1024**2)
        if name == 'fat':
            run('mkfs.vfat', '-F', '32', work / (name+'.img'))
        else:
            run('mkfs.ext4', '-q', '-F', '-d', seeds / ('source' if name == 'writer' else name), work / (name+'.img'))
    shutil.copyfile(work / 'fat.img', work / 'replacement.img')
    images = {str(p): [p.stat().st_dev, p.stat().st_ino, p.stat().st_size] for p in work.glob('*.img')}
    fixture = dict(base=str(work), root=str(work / 'recovery'), lock=str(work / 'run/media.lock'), images=images)
    (work / 'disposable-recovery-fixture.json').write_text(json.dumps(fixture))
    loops, mounted = {}, set()
    def mount(name, options, target=None):
        target = target or name
        run('mount', '-o', options, loops[name], work / target)
        mounted.add(target)
    def unmount(name, lazy=False):
        run('umount', *(['-l'] if lazy else []), work / name)
        mounted.remove(name)
    try:
        # Preparation is a participating mutator and uses exactly the same lock
        # as the exporter. None of these commands is in production runtime.
        with MediaLease(work / 'run/media.lock'):
            for name in ('recovery', 'source', 'fat', 'writer'):
                loops[name] = run('losetup', '--find', '--show', *(['--read-only'] if name in ('recovery', 'source') else []), work / (name+'.img'))
            mount('recovery', 'ro,noload,noatime,nosuid,nodev,noexec')
            mount('source', 'ro,noload,noatime,nosuid,nodev,noexec')
            mount('fat', 'rw,nosuid,nodev,noexec,umask=0077')
        before_source = digest(work / 'source.img')
        before_root = digest(work / 'recovery.img')
        target = work / 'fat'
        (target / 'keep.txt').write_bytes(b'existing destination data')
        (target / '.older.partial').write_bytes(b'older interrupted operation')
        keep = {p.name: p.read_bytes() for p in target.iterdir()}
        kernel = Kernel()
        selected = {m['path']: m for m in kernel.mounts()}
        policy = dict(format_version=1, kind='disposable-recovery-fixture', protocol=PROTOCOL,
                      writer_model=WRITER_MODEL, image_manifest_sha256=hashlib.sha256(manifest).hexdigest(),
                      recovery=durable_identity(kernel.block(selected[str(work / 'recovery')], fixture)),
                      source=durable_identity(kernel.block(selected[str(work / 'source')], fixture)))
        policy['system_media'] = [policy['recovery']['stable'], policy['source']['stable']]
        context = dict(format_version=1, protocol=PROTOCOL, policy_sha256=fingerprint(policy),
                       source=str(work / 'source'), destinations={'fixture-fat': dict(path=str(target), label='Disposable FAT medium')})
        provider = MediaProvider(policy, context, fixture=fixture)
        context['expected'] = provider.snapshot()
        initial = copy.deepcopy(context['expected'])
        (work / 'run/media-context.json').write_text(json.dumps(context))
        exporter = provider.exporter
        events = []

        # Real processes compete on the same admission file, including at final
        # publication and directory fsync. No unused fixture-only lock exists.
        code = ('import sys;sys.path.insert(0,sys.argv[1]);from sv08_recovery_media import MediaLease;'
                '\ntry:\n with MediaLease(sys.argv[2]): print("acquired",flush=True);sys.stdin.read(1)'
                '\nexcept ValueError: print("busy",flush=True)')
        def competitor():
            return subprocess.Popen(['/usr/bin/python3', '-c', code, str(REPO / 'runtime'), str(work / 'run/media.lock')],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        held = competitor()
        assert held.stdout.readline().strip() == 'acquired'
        try:
            refused(lambda: exporter.prepare('fixture-fat'), 'owns admission')
        finally:
            held.communicate('x', timeout=10)
        events.append('competing-media-process-refused')
        def assert_locked():
            child = competitor()
            output, _ = child.communicate('x', timeout=10)
            assert output.strip() == 'busy', output

        from sv08_recovery_ui import RecoveryWindow, Gtk, GLib
        from sv08_recovery import RecoveryController
        from sv08_state import Store
        window = RecoveryWindow(RecoveryController(Store(work / 'source/sv08'), provider))
        window.show_all()
        def wait(condition):
            deadline = time.monotonic()+30
            while not condition():
                while Gtk.events_pending():
                    Gtk.main_iteration_do(False)
                if time.monotonic() > deadline:
                    raise AssertionError('GTK timeout: '+window.message.get_text()+' '+window.reason.get_text())
                time.sleep(.01)
        wait(lambda: not window.busy)
        assert 'damaged' in window.message.get_text()
        assert window.buttons[3][0].get_sensitive(), window.reason.get_text()
        def drive(choice):
            responses = []
            def answer():
                for dialog in Gtk.Window.list_toplevels():
                    if isinstance(dialog, Gtk.Dialog) and dialog.get_visible():
                        review = isinstance(dialog, Gtk.MessageDialog)
                        if review:
                            assert 'private configuration' in dialog.get_property('secondary-text')
                        responses.append('review' if review else 'chooser')
                        cancel = choice == 'cancel-chooser' or (review and choice == 'cancel-review')
                        dialog.response(Gtk.ResponseType.CANCEL if cancel else Gtk.ResponseType.OK)
                        return not (review or cancel)
                return True
            GLib.timeout_add(25, answer)
            window.buttons[3][0].clicked()
            wait(lambda: not window.busy and len(responses) == (1 if choice == 'cancel-chooser' else 2))
            events.append('gtk-'+choice)
        drive('cancel-chooser')
        assert {p.name: p.read_bytes() for p in target.iterdir()} == keep
        drive('cancel-review')
        assert {p.name: p.read_bytes() for p in target.iterdir()} == keep
        original_publish, original_fsync = sv08_export.publish, os.fsync
        def publish(*args):
            assert_locked()
            result = original_publish(*args)
            events.append('lease-held-through-publication')
            return result
        def fsync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                assert_locked()
                events.append('lease-held-through-directory-fsync')
            return original_fsync(fd)
        with patch('sv08_export.publish', publish), patch('sv08_export.os.fsync', fsync):
            drive('apply')
        assert 'readback verified' in window.message.get_text(), window.message.get_text()
        window.hide()
        archive = next(target.glob('*.tar'))
        with tarfile.open(archive) as stream:
            assert stream.extractfile('data/sv08/state.json').read() == b'damaged registry remains exportable'
            assert stream.extractfile('data/printer.cfg').read() == b'private fixture configuration'
        existing_names = {p.name for p in target.iterdir()}

        # Shared source validation: writable backing bind, aliases and submounts.
        with MediaLease(work / 'run/media.lock'):
            run('mount', '--bind', work / 'source', work / 'alias')
            mounted.add('alias')
        refused(lambda: exporter.prepare('fixture-fat'), 'alias')
        with MediaLease(work / 'run/media.lock'):
            unmount('alias')
            unmount('source')
            mount('writer', 'rw,nosuid,nodev,noexec')
            run('mount', '--bind', work / 'writer', work / 'source')
            mounted.add('source')
            run('mount', '-o', 'remount,bind,ro', work / 'source')
        refused(lambda: exporter.prepare('fixture-fat'), 'alias')
        with MediaLease(work / 'run/media.lock'):
            unmount('source')
            unmount('writer')
            mount('source', 'ro,noload,noatime,nosuid,nodev,noexec')
        context['expected'] = provider.snapshot()
        events.extend(['source-alias-refused', 'readonly-bind-writable-backing-refused'])

        # Synthetic changes supplement real mounts; never replace their success
        # path. They exercise specific fail-closed branches without other media.
        actual_mounts = kernel.mounts()
        bad = copy.deepcopy(actual_mounts)
        source_mount = next(m for m in bad if m['path'] == str(work / 'source'))
        source_mount['super_options'] = ['rw']
        with patch.object(provider.kernel, 'mounts', return_value=bad):
            refused(lambda: exporter.prepare('fixture-fat'), 'superblock')
        events.append('inconsistent-vfs-superblock-refused')
        original_block = provider.kernel.block
        refused(lambda: kernel.block(selected[str(work / 'source')]), 'Unsupported virtual/stacked')
        def writable_medium(mount, fixture):
            value = original_block(mount, fixture)
            if mount['path'] == str(work / 'source'):
                value['disk_readonly'] = False
            return value
        with patch.object(provider.kernel, 'block', writable_medium):
            refused(lambda: exporter.prepare('fixture-fat'), 'whole medium')
        events.extend(['unsupported-production-loop-stack-refused', 'writable-source-whole-medium-refused'])
        def nonremovable(mount, fixture):
            value = original_block(mount, fixture)
            if mount['path'] == str(target):
                value['stable'] = {'device/serial': 'nonremovable-fixture-double'}
                value['removable'] = False
            return value
        with patch.object(provider.kernel, 'block', nonremovable):
            refused(lambda: exporter.prepare('fixture-fat'), 'not a removable')
        def same_medium(mount, fixture):
            value = original_block(mount, fixture)
            if mount['path'] == str(target):
                value['disk'] = context['expected']['source']['block']['disk']
            return value
        with patch.object(provider.kernel, 'block', same_medium):
            refused(lambda: exporter.prepare('fixture-fat'), 'shares a system/source')
        events.extend(['nonremovable-destination-refused', 'same-source-medium-refused'])

        # An actual unexpected userspace mount namespace refuses admission.
        child = subprocess.Popen(['unshare', '--mount', '/usr/bin/python3', '-c',
                                  'import sys;print("ready",flush=True);sys.stdin.read(1)'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        assert child.stdout.readline().strip() == 'ready'
        try:
            refused(lambda: exporter.prepare('fixture-fat'), 'namespace')
        finally:
            child.communicate('x', timeout=10)
        events.append('unexpected-process-namespace-refused')

        # Unexpected submounts in exported data are never traversed.
        with MediaLease(work / 'run/media.lock'):
            run('mount', '-t', 'tmpfs', 'tmpfs', work / 'source/sv08')
            mounted.add('source/sv08')
        refused(lambda: exporter.prepare('fixture-fat'), 'submount')
        with MediaLease(work / 'run/media.lock'):
            unmount('source/sv08')
        context['expected'] = provider.snapshot()
        events.append('source-submount-refused')

        # Device-number reuse can also be signaled while paths and directory
        # descriptors still agree. Inject only that kernel identity observation.
        plan = exporter.prepare('fixture-fat')
        changed = False
        original_verify = sv08_export.verify_archive
        def change_identity(*args):
            nonlocal changed
            original_verify(*args)
            changed = True
        def changed_block(mount, fixture):
            value = original_block(mount, fixture)
            if changed and mount['path'] == str(target):
                value['diskseq'] += 1
            return value
        with patch('sv08_export.verify_archive', change_identity), patch.object(provider.kernel, 'block', changed_block):
            refused(lambda: exporter.execute(plan), 'changed during export')
        assert {p.name for p in target.iterdir()} == existing_names
        events.append('injected-mid-execution-diskseq-change-no-publication')

        # Disappearance after verification must not publish; held descriptors
        # still allow deletion of this operation's partial on detached FAT.
        plan = exporter.prepare('fixture-fat')
        def disappear(*args):
            original_verify(*args)
            unmount('fat', lazy=True)  # Deliberate nonparticipant failure injection.
        with patch('sv08_export.verify_archive', disappear):
            refused(lambda: exporter.execute(plan), 'changed')
        with MediaLease(work / 'run/media.lock'):
            mount('fat', 'rw,nosuid,nodev,noexec,umask=0077')
        assert {p.name for p in target.iterdir()} == existing_names
        context['expected'] = provider.snapshot()
        events.append('mid-execution-removal-no-publication-lease-released')

        # Same major:minor, same filesystem UUID, different loop backing/diskseq.
        review = exporter.prepare('fixture-fat')
        before = context['expected']['destinations']['fixture-fat']['block']
        with MediaLease(work / 'run/media.lock'):
            unmount('fat')
            run('losetup', '-d', loops['fat'])
            run('losetup', loops['fat'], work / 'replacement.img')
            mount('fat', 'rw,nosuid,nodev,noexec,umask=0077')
        after = provider.snapshot()['destinations']['fixture-fat']['block']
        assert before['device'] == after['device'] and before['filesystem_uuid'] == after['filesystem_uuid']
        assert before['diskseq'] != after['diskseq']
        refused(lambda: exporter.execute(review), 'changed')
        assert not list(target.glob('*.tar'))
        with MediaLease(work / 'run/media.lock'):
            unmount('fat')
            run('losetup', '-d', loops['fat'])
            run('losetup', loops['fat'], work / 'fat.img')
            mount('fat', 'rw,nosuid,nodev,noexec,umask=0077')
        context['expected'] = provider.snapshot()
        events.append('device-number-reuse-between-review-apply-refused')

        assert digest(work / 'source.img') == before_source
        assert digest(work / 'recovery.img') == before_root
        assert all((target / name).read_bytes() == data for name, data in keep.items())
        assert {p.name for p in target.iterdir()} == existing_names
        with MediaLease(work / 'run/media.lock'):
            pass
        result = dict(passed=True, physical_hardware=False, fixture_root_exception=True,
                      source_mount_and_superblock_readonly=True, source_whole_block_readonly=True,
                      source_image_unchanged=True, recovery_image_unchanged=True,
                      damaged_registry_preserved=True, existing_destination_preserved=True,
                      archive_bytes=archive.stat().st_size, archive_sha256=digest(archive),
                      events=events, initial_media_fingerprint=fingerprint(initial))
        (work / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
    finally:
        # Only these fixture mounts/nodes; never enumerate/detach other loops.
        with MediaLease(work / 'run/media.lock'):
            for name in sorted(mounted, key=lambda name: len(Path(name).parts), reverse=True):
                run('umount', work / name)
            for loop in loops.values():
                run('losetup', '-d', loop)
            if (work / 'result.json').exists():
                for image in images:
                    Path(image).unlink()


if __name__ == '__main__':
    main()
