#!/usr/bin/env python3
"""Installed disposable guest acceptance driver; never a production service.

Run recovery phases on the same target across guest restarts. The normal-role
fixture runs the rendered initramfs identity hook before PID 1 and the actual
sv08_boot.py --execute systemd unit; normal-assert observes its configuration,
identity and mounts. Legacy normal-restored/normal-previous phases are narrower
boot-contract probes. This does not qualify a full printing OS or hardware.
Every phase requires the explicit disposable marker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from sv08_recovery import installed_controller
from sv08_recovery_restore_media import POLICY
from sv08_recovery_activation import boot_guard
from sv08_state import Store


def configuration(root):
    store=Store(root); state=store.load(); return (store.generation_path(state['slots']['A'])/'config/printer.cfg').read_text()


def inject_activation_boundary(controller, boundary):
    """Keep test-only failure injection across real provider factory refreshes."""
    factory = controller._adapter_factory
    if factory is None:
        raise AssertionError('Installed recovery adapter factory required')
    def refresh():
        adapter, store = factory()  # Preserve production provider/admission setup.
        adapter.restore.activation.boundary = boundary
        return adapter, store
    controller._adapter_factory = refresh


def widget_action(controller,action,arguments,cancel=False,timeout=30):
    """Actual installed widgets/controller/provider, with inspectable review."""
    import time
    from sv08_recovery_ui import RecoveryWindow, Gtk, GLib, Gdk
    window=RecoveryWindow(controller);window.show_all()
    def wait(condition):
        deadline=time.monotonic()+timeout
        while not condition():
            while Gtk.events_pending(): Gtk.main_iteration_do(False)
            if time.monotonic()>deadline: raise AssertionError('Installed GTK timeout')
            time.sleep(.01)
    wait(lambda:not window.busy)
    seen=[]
    def dialogs():
        for dialog in Gtk.Window.list_toplevels():
            if not isinstance(dialog,Gtk.Dialog): continue
            if isinstance(dialog,Gtk.MessageDialog):
                seen.append(True)
                print('SV08_RESTORE_UI_REVIEW '+action+(' cancel' if cancel else ' apply'),flush=True)
                # Coordinator may capture QMP screendump during this real review.
                while Gtk.events_pending(): Gtk.main_iteration_do(False)
                time.sleep(2)
                dialog.response(Gtk.ResponseType.CANCEL if cancel else Gtk.ResponseType.OK)
                return False
            dialog.response(Gtk.ResponseType.OK)
        return True
    GLib.timeout_add(30,dialogs)
    button=next(button for button,key in window.buttons if key==action)
    assert button.get_sensitive(), window.reason.get_text()
    button.grab_focus();button.activate();wait(lambda:bool(seen) and not window.busy)
    if not cancel:
        text=window.message.get_text()
        assert any(word in text for word in ('restored','activated','created')), text
    print('SV08_RESTORE_UI_RESULT '+window.message.get_text(),flush=True)
    time.sleep(2);window.hide()


def assert_actual_normal_boot():
    """Observe the real PID 1 boot unit's output, mounts and application view."""
    assert Path('/proc/1/comm').read_text().strip()=='systemd'
    boot=json.loads(Path('/run/sv08/boot.json').read_text())
    arguments=Path('/proc/cmdline').read_text().split()
    expected=[a.split('=',1)[1] for a in arguments if a.startswith('sv08.e2e.expect=')]
    assert len(expected)==1 and expected[0] in ('restored','previous')
    configuration_text=expected[0]+' fixture configuration'
    assert Path('/run/sv08/printer_data/config/printer.cfg').read_text()==configuration_text
    assert boot['mode']=='immutable' and boot['slot']=='A'
    assert boot['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    identity=('b' if expected[0]=='restored' else 'a')*32+'\n'
    assert Path('/etc/machine-id').read_text()==Path('/data/sv08/system/machine-id').read_text()==identity
    for path,filesystem,mode in [('/','ext4','ro'),('/usr','squashfs','ro'),('/data','ext4','rw'),('/boot','vfat','ro')]:
        row=subprocess.check_output(['findmnt','-n','-o','FSTYPE,OPTIONS','--mountpoint',path],text=True).strip().split()
        assert row[0]==filesystem and mode in row[1].split(','),(path,row)
    print('SV08_ACTUAL_NORMAL_BOOT '+json.dumps(dict(result='PASS',expected=expected[0],slot=boot['slot'],mode=boot['mode'],generation=boot['generation'],boot_id=boot['boot_id'])),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('restore','normal-restored','rollback','normal-previous','wrong-target','normal-assert','interrupt'),required=True)
    parser.add_argument('--disposable-marker',type=Path,required=True)
    parser.add_argument('--hook',type=Path)
    parser.add_argument('--gtk',action='store_true',help='Exercise installed native GTK for restore/activation/rollback')
    parser.add_argument('--gtk-timeout',type=int,default=30,help='Per-widget-operation deadline for installed emulation, 1–180 seconds')
    args=parser.parse_args()
    if not 1 <= args.gtk_timeout <= 180:parser.error('GTK timeout must be 1–180 seconds')
    if args.disposable_marker.read_text() != 'sv08-disposable-restore-e2e-v1\n': parser.error('Disposable guest marker required')
    if args.phase=='normal-assert':
        assert_actual_normal_boot();return
    policy=json.loads(POLICY.read_text());spec=policy['targets']['target'];target=Path(spec['mount']);boot=policy['boot']
    source=Path(policy['archives']['backup']['path']); archive_before=hashlib.sha256(source.read_bytes()).hexdigest()
    if args.phase in ('restore','rollback','wrong-target','interrupt'):
        controller=installed_controller()
        if args.phase=='interrupt':
            # The previously booted restored tree retains systemd log links.
            # Exercise the supported fresh activation route without changing
            # either running/retained state or strict archive candidate rules.
            controller.apply(controller.plan('recovery.initialize',dict(target='target')))
            controller.status()
            def cut(boundary):
                if boundary=='saved':raise RuntimeError('disposable activation power cut after saving old state')
            inject_activation_boundary(controller,cut)
            try:controller.apply(controller.plan('recovery.activate-fresh',dict(target='target')))
            except RuntimeError as error:assert 'power cut' in str(error)
            else:raise AssertionError('Interruption was not injected')
            assert (target/'.sv08-activation-pending').is_file()
            assert not (target/'sv08').exists()
        elif args.phase=='wrong-target':
            try: controller.plan('recovery.data-restore',dict(archive='backup',target='unreviewed-target'))
            except ValueError: pass
            else: raise AssertionError('Wrong target admitted')
            assert not (target/'restored').exists()
        elif args.phase=='restore':
            before=configuration(target/'sv08');assert before=='previous fixture configuration'
            plan=controller.plan('recovery.data-restore',dict(archive='backup',target='target'))
            assert not (target/'restored').exists()  # review/cancel performs no writes
            if args.gtk:
                widget_action(controller,'recovery.data-restore',dict(archive='backup',target='target'),cancel=True,timeout=args.gtk_timeout)
                assert not (target/'restored').exists()
                widget_action(controller,'recovery.data-restore',dict(archive='backup',target='target'),timeout=args.gtk_timeout)
            else: controller.apply(plan)
            assert configuration(target/'restored/sv08')=='restored fixture configuration'
            plan=controller.plan('recovery.activate',dict(target='target'))
            assert configuration(target/'sv08')==before
            if args.gtk:
                widget_action(controller,'recovery.activate',dict(target='target'),cancel=True,timeout=args.gtk_timeout)
                assert configuration(target/'sv08')==before
                widget_action(controller,'recovery.activate',dict(target='target'),timeout=args.gtk_timeout)
            else: controller.apply(plan)
            boot_guard(target)
            assert configuration(target/'sv08')=='restored fixture configuration'
            assert (target/'restored/preserved-sibling').read_text()=='archive container sibling'
        else:
            if args.gtk: widget_action(controller,'recovery.rollback',dict(target='target'),timeout=args.gtk_timeout)
            else: controller.apply(controller.plan('recovery.rollback',dict(target='target')))
            boot_guard(target);assert configuration(target/'sv08')=='previous fixture configuration'
        assert (target/'keep').read_text()=='target sibling unchanged'
    else:
        if not args.hook: parser.error('Normal contract probe requires exact hook source')
        identity=(target/'sv08/system/machine-id').read_text()
        # Releasing recovery's target mount precedes fsck/mount by the initramfs hook.
        block=policy['targets']['target']['identity']
        inventory=json.loads(Path('/run/sv08-recovery/restore-context.json').read_text())['expected']['targets']['target']['block']
        device='/dev/disk/by-partuuid/'+inventory['partuuid']
        subprocess.run(['umount',str(target)],check=True)
        normal=Path('/run/sv08-e2e-normal-root');normal.mkdir(mode=0o700)
        (normal/'data').mkdir(mode=0o700);(normal/'etc').mkdir(mode=0o700)
        (normal/'etc/machine-id').touch();(normal/'etc/hostname').touch()
        functions=normal/'functions';functions.write_text('panic() { echo "SV08_E2E_PANIC $*"; exit 91; }\n')
        hook=args.hook.read_text().replace('@DATA_DEVICE@',device).replace('. /scripts/functions','. '+str(functions))
        rendered=normal/'sv08-data';rendered.write_text(hook)
        subprocess.run(['/bin/sh',str(rendered)],env=dict(os.environ,rootmnt=str(normal)),check=True,timeout=40)
        root=normal/'data/sv08';boot_guard(root.parent)
        assert (normal/'etc/machine-id').read_text()==identity
        store=Store(root);store.initialize()
        prepared=store.prepare_boot(boot['slot'],boot['release'],boot['state_schema'],boot['release_revision'])
        expected='restored fixture configuration' if args.phase=='normal-restored' else 'previous fixture configuration'
        assert configuration(root)==expected
        assert (Path(prepared['generation'])/'config/printer.cfg').read_text()==expected
        assert prepared['mode']=='immutable'
        # Caller shuts down this guest; durable target is reused by the next phase.
    assert hashlib.sha256(source.read_bytes()).hexdigest()==archive_before
    print('SV08_RESTORE_E2E '+json.dumps(dict(phase=args.phase,result='PASS',archive_sha256=archive_before)),flush=True)

if __name__=='__main__': main()
