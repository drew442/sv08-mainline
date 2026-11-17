"""Explicit supported Klipper-start permission, separate from print qualification.

No MCU access or output command. A root operator records the reviewed
physical-operation reference only after the project's external gate. Authorize
does not operate services; boot-activate queues only an already permitted start.
Normal SAVE_CONFIG drift stays under the existing native calibration contract.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from sv08_printer_catalog import digest, strict_json
from sv08_printer_publish import Publisher
from sv08_restart import start_admitted
from sv08_state import Store, atomic_json, fsync_dir

RELEASE = Path('/usr/lib/sv08/release.json')
ROOT = Path('/data/sv08')
RUNTIME = Path('/run/sv08')


def read(path, limit=65536, uid=0):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unexpected commissioning input link')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1 or
                info.st_mode & 0o022 or info.st_size > limit):
            raise ValueError('Invalid commissioning input')
        return strict_json(os.read(fd, limit+1), limit)
    finally: os.close(fd)


class Commissioning:
    def __init__(self, store, release=RELEASE, runtime=RUNTIME, uid=0, source=None):
        self.store, self.release, self.runtime, self.uid = store, Path(release), Path(runtime), uid
        self.source = source
        self.permission = store.root/'system/klipper-start.json'

    def snapshot(self):
        from sv08_printer_firmware import validate_assignment
        manifest = read(self.release, uid=self.uid)
        if manifest.get('commissioning') != 'explicit-v1' or manifest.get('owner_setup') != 'recovery-v1':
            raise ValueError('This is not the supported commissioning profile')
        boot = read(self.runtime/'boot.json', uid=self.uid)
        state = self.store.load()
        if (boot.get('trial') is not False or boot.get('slot') not in ('A', 'B') or
                not (self.runtime/'os-health-ready').is_file() or (self.runtime/'trial').exists() or
                state.get('pending') is not None):
            raise ValueError('Commissioning requires a healthy normal boot without an image transaction')
        record = state['slots'].get(boot['slot'])
        if not record or record['release'] != boot.get('release') or boot['release'] != manifest['release']:
            raise ValueError('Commissioning boot and release differ')
        generation = self.store.generation_path(record)
        if str(generation) != boot.get('generation'): raise ValueError('Commissioning generation changed')
        assignment = validate_assignment(manifest['mcu_firmware'], manifest['release'])
        publisher = Publisher(generation/'config', source=self.source)
        receipt, _, _, _ = publisher.active_calibration(dict(generation=str(generation)))
        binding = receipt['native'].get('binding')
        if not isinstance(binding, dict) or not binding.get('hardware') or not binding.get('firmware_boards'):
            raise ValueError('Apply a complete managed hardware configuration before commissioning')
        permission = dict(format_version=1, publication=receipt['review'], binding=binding,
                          host_klipper_commit=assignment['host_klipper_commit'])
        review = dict(permission=permission, boot=boot,
                      effect='Permit Klipper startup for this reviewed configuration. This does not certify printing, measured MCU compatibility or authorize an output command. System updates and rollback never flash MCU firmware.')
        return dict(review=review, review_sha256=digest(review))

    def authorize(self, expected, assessment):
        if not isinstance(assessment, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/ -]{0,159}', assessment):
            raise ValueError('Provide the exact physical-operation assessment reference')
        current = self.snapshot()
        if expected != current['review_sha256']: raise ValueError('Commissioning review changed; review again')
        directory = self.permission.parent
        info = directory.lstat()
        if directory.is_symlink() or info.st_uid != self.uid or info.st_mode & 0o022:
            raise ValueError('Commissioning permission storage must remain privileged')
        if self.permission.exists() or self.permission.is_symlink(): self.permission_record()
        atomic_json(self.permission, dict(**current['review']['permission'], assessment=assessment))
        return dict(saved=True, service_action='none', printing_qualified=False)

    def permission_record(self):
        value = read(self.permission, limit=65536, uid=self.uid)
        if (set(value) != {'format_version', 'publication', 'binding', 'host_klipper_commit', 'assessment'} or
                stat.S_IMODE(self.permission.stat().st_mode) != 0o600):
            raise ValueError('Invalid commissioning permission; no repair was attempted')
        return value

    def check(self):
        current = self.snapshot()['review']['permission']
        try: recorded = self.permission_record()
        except FileNotFoundError:
            raise ValueError('Klipper start requires a separately reviewed commissioning permission') from None
        if {key:value for key,value in recorded.items() if key != 'assessment'} != current:
            raise ValueError('Hardware publication or host/MCU recommendation changed; review compatibility before starting Klipper. MCU firmware was not flashed.')
        return dict(permitted=True, printing_qualified=False)

    def boot_activate(self, command=None):
        """Queue a guarded boot start, never create or repair permission.

        Release the locks before dispatch so Klipper's ExecStartPre can acquire
        them. That execution-time check closes changes after this observation.
        Never wait for service completion or hold a boot dependency job open.
        """
        try:
            with self.store.locked(nonblocking=True), start_admitted(self.runtime):
                self.check()
        except (ValueError, OSError) as error:
            return dict(service_action='none', reason=str(error), printing_qualified=False)
        (command or subprocess.run)(['/usr/bin/systemctl', '--no-block', 'start', 'sv08-klipper.service'],
                                    check=True, timeout=15)
        return dict(service_action='start-queued', printing_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('review', 'authorize', 'check', 'revoke', 'boot-activate'))
    parser.add_argument('--review-sha256')
    parser.add_argument('--assessment')
    args = parser.parse_args()
    if os.geteuid() != 0: parser.error('Root administration is required')
    store = Store(ROOT)
    service = Commissioning(store)
    if args.action == 'boot-activate':
        print(json.dumps(service.boot_activate()))
        return
    # State before service admission is the existing lock order.
    with store.locked(nonblocking=True), start_admitted(RUNTIME):
        if args.action == 'review': result = service.snapshot()
        elif args.action == 'authorize': result = service.authorize(args.review_sha256, args.assessment)
        elif args.action == 'check': result = service.check()
        else:
            if service.permission.exists() or service.permission.is_symlink():
                service.permission_record(); service.permission.unlink(); fsync_dir(service.permission.parent)
            result = dict(revoked=True, service_action='none')
    print(json.dumps(result))


if __name__ == '__main__': main()
