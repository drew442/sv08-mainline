#!/usr/bin/env python3
"""Validated RAUC backend for the persistent update transaction coordinator.

No command-line activation. Callers supply reviewed image/policy/layout inputs
and hold the transaction/admission locks. Hardware access is refused for ordinary
non-deployable manifests; the sole fixture exception requires an identified VM.
"""
import configparser
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from sv08_boot import verify_devices
from sv08_gpt import inspect as inspect_gpt
from sv08_bundle import inspect as inspect_bundle

MIB = 1024*1024
CLEANUP_SECONDS = 10
SLOT_NAMES = {'rootfs.0': ('root-a', 'ext4', 'A', None),
              'boot.0': ('boot-a', 'vfat', None, 'rootfs.0'),
              'rootfs.1': ('root-b', 'ext4', 'B', None),
              'boot.1': ('boot-b', 'vfat', None, 'rootfs.1')}


def validate_config(text, manifest, policy, keyring):
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(text)
    if set(config.sections()) != {'system', 'keyring', *('slot.'+name for name in SLOT_NAMES)}:
        raise ValueError('Unexpected RAUC sections or handlers')
    required = {'compatible': policy['compatible'], 'bootloader': 'uboot',
                'bundle-formats': 'verity', 'activate-installed': 'false',
                'boot-attempts': '3', 'boot-attempts-primary': '3',
                'data-directory': '/var/lib/rauc', 'perform-pre-check': 'true'}
    if dict(config['system']) != required or dict(config['keyring']) != {'path': str(keyring)}:
        raise ValueError('RAUC must use the reviewed non-activating paired update configuration')
    for name, (role, kind, bootname, parent) in SLOT_NAMES.items():
        expected = {'device': manifest['devices'][role], 'type': kind}
        expected.update({'bootname': bootname} if bootname else {'parent': parent})
        if dict(config['slot.'+name]) != expected:
            raise ValueError('RAUC slot configuration differs from the image manifest: '+name)


def validate_status(status, manifest, policy, boot):
    if status['compatible'] != policy['compatible'] or status['booted'] != boot['slot'] or status.get('variant'):
        raise ValueError('RAUC service is managing a different running target')
    slots = {}
    for item in status['slots']:
        if len(item) != 1 or set(item) & set(slots):
            raise ValueError('Duplicate or malformed RAUC slot status')
        slots.update(item)
    if set(slots) != set(SLOT_NAMES):
        raise ValueError('RAUC must manage exactly the paired boot/root slots')
    for name, (role, kind, bootname, parent) in SLOT_NAMES.items():
        actual = slots[name]
        if (actual['class'] != name.split('.')[0] or actual['device'] != manifest['devices'][role] or actual['type'] != kind or
                actual['bootname'] != bootname or actual['parent'] != parent):
            raise ValueError('Running RAUC service has different slot devices or grouping')
        active = role.endswith(boot['slot'].lower())
        expected_state = ('booted' if bootname else 'active') if active else 'inactive'
        if actual['state'] != expected_state:
            raise ValueError('RAUC active/inactive grouping disagrees with the running root')
        if not active and actual['mountpoint'] is not None:
            raise ValueError('Inactive slot is mounted')
    return slots



def validate_environment(values, layout_id):
    if (set(values) != {'sv08_env_layout', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT'} or
            values['sv08_env_layout'] != layout_id or values['BOOT_ORDER'] not in ('A B', 'B A', 'A', 'B') or
            values['BOOT_A_LEFT'] not in ('0', '1', '2', '3') or values['BOOT_B_LEFT'] not in ('0', '1', '2', '3')):
        raise ValueError('Persistent environment layout/order/counters are invalid')


def block_info(path):
    st = os.stat(path)
    if not stat.S_ISBLK(st.st_mode):
        raise ValueError('Slot is not a block device')
    number = f'{os.major(st.st_rdev)}:{os.minor(st.st_rdev)}'
    node = (Path('/sys/dev/block') / number).resolve(strict=True)
    return dict(number=number, parent=node.parent, partition=int((node/'partition').read_text()),
                size=int((node/'size').read_text())*512, start=int((node/'start').read_text())*512)



def validate_geometry(info, layout, policy):
    roles = ['boot-a', 'root-a', 'boot-b', 'root-b', 'recovery', 'data']
    if (policy['layout'] != 'ab-8gb-v1' or [part['name'] for part in layout['partitions']] != roles or
            set(info) != set(roles) or len({v['number'] for v in info.values()}) != 6 or
            len({v['parent'] for v in info.values()}) != 1):
        raise ValueError('Expected six distinct reviewed partitions on one device')
    offset = layout['leading_reservation_mib']*MIB
    if offset != 16*MIB:
        raise ValueError('Unreviewed leading reservation')
    for index, part in enumerate(layout['partitions'], 1):
        actual = info[part['name']]
        if (actual['partition'] != index or actual['size'] != part['mib']*MIB or
                actual['start'] != offset):
            raise ValueError('Actual partition geometry differs from the reviewed layout')
        offset += actual['size']
    if offset + layout['tail_reservation_mib']*MIB != layout['image_bytes']:
        raise ValueError('Layout does not fit its declared image footprint')
    if (policy['image_bytes'] != {'boot': info['boot-a']['size'], 'rootfs': info['root-a']['size']} or
            info['boot-a']['size'] != info['boot-b']['size'] or info['root-a']['size'] != info['root-b']['size']):
        raise ValueError('Bundle policy does not describe complete equal-sized slot pairs')
    return info['root-a']['parent']


def digest_device(path, size):
    digest = hashlib.sha256()
    with open(path, 'rb', buffering=0) as stream:
        while size:
            block = stream.read(min(size, 8*MIB))
            if not block:
                raise ValueError('Short read from slot')
            digest.update(block); size -= len(block)
    return digest.hexdigest()


class Backend:
    def __init__(self, manifest, policy, layout, environment,
                 config=Path('/etc/rauc/system.conf'), keyring=Path('/etc/rauc/release-keyring.pem'),
                 env_config=Path('/etc/fw_env.config'), fixture=False):
        self.manifest, self.policy, self.layout, self.environment = manifest, policy, layout, environment
        self.config, self.keyring, self.env_config, self.fixture = config, keyring, env_config, fixture
        self.boot = None

    def command(self, *args):
        return subprocess.check_output(['/usr/bin/rauc', '--conf='+str(self.config), *args], text=True)

    def status(self, read_command=None):
        if read_command:
            return json.loads(read_command(['/usr/bin/rauc', '--conf='+str(self.config), 'status', '--output-format=json'], text=True))
        return json.loads(self.command('status', '--output-format=json'))

    def validate_context(self, boot, read_command=None):
        if os.geteuid() != 0:
            raise ValueError('RAUC backend operations require root')
        if self.fixture:
            if ('sv08.test=rauc-backend' not in Path('/proc/cmdline').read_text().split() or
                    (read_command or subprocess.check_output)(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu' or
                    Path('/sys/block/vda/serial').read_text().strip() != 'SV08-QEMU-DISPOSABLE' or
                    self.manifest.get('deployable') is not False):
                raise ValueError('Backend fixture requires the identified disposable VM')
        elif (self.manifest.get('deployable') is not True or
              type(self.environment['board_mmc_device_index']) is not int or
              not 0 <= self.environment['board_mmc_device_index'] <= 31 or
              self.policy['compatible'].startswith('sv08-offline')):
            raise ValueError('Backend requires a reviewed deployable board manifest')
        if not os.statvfs('/').f_flag & os.ST_RDONLY or boot['mode'] != 'immutable':
            raise ValueError('Image backend requires an immutable running root')
        if self.manifest['release'] != boot['release'] or self.manifest['state_schema'] != self.policy['state_schema']:
            raise ValueError('Running release/schema differs from update policy')
        packaged = json.loads(Path('/usr/share/doc/sv08-klipper/release.json').read_text())
        if packaged['source_commit'] != self.policy['klipper_commit']:
            raise ValueError('Installed host Klipper differs from the permitted MCU-compatible pin')
        verify_devices(self.manifest, boot['slot'], read_command=read_command)
        validate_config(self.config.read_text(), self.manifest, self.policy, self.keyring)
        info = {name: block_info(path) for name, path in self.manifest['devices'].items()}
        parent = validate_geometry(info, self.layout, self.policy)
        if int((parent/'size').read_text())*512 < self.layout['image_bytes']:
            raise ValueError('Root device is smaller than the image footprint')
        if int((parent/'removable').read_text()) != 0:
            raise ValueError('Refusing a removable root medium')
        # libubootenv must address the same whole device, in the reviewed leading
        # reservation. No boot partition file environment or inferred offsets.
        environment = self.environment
        if (environment['layout_id'] != self.policy['layout'] or environment['medium'] != 'mmc-user-area' or
                environment['size_bytes'] != 65536 or environment['copy_offsets_bytes'] != [4*MIB, 8*MIB] or
                self.layout['leading_reservation_mib'] != 16):
            raise ValueError('Unreviewed redundant environment layout')
        entries = [line.split() for line in self.env_config.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
        if len(entries) != 2:
            raise ValueError('Expected exactly two raw environment copies')
        for entry, offset in zip(entries, environment['copy_offsets_bytes']):
            if len(entry) != 3 or int(entry[1], 0) != offset or int(entry[2], 0) != environment['size_bytes']:
                raise ValueError('Unexpected environment offsets/size/options')
            device = os.stat(entry[0])
            if not stat.S_ISBLK(device.st_mode) or (parent/'dev').read_text().strip() != f'{os.major(device.st_rdev)}:{os.minor(device.st_rdev)}':
                raise ValueError('Environment is on a different block device')
        gpt = inspect_gpt(Path(entries[0][0]), allow_block=True,
            image_bytes=self.layout['image_bytes'], environment_regions=[
                (offset, environment['size_bytes']) for offset in environment['copy_offsets_bytes']])
        expected_records = [dict(number=info[part['name']]['partition'], name=part['name'],
            partuuid=self.manifest['devices'][part['name']].rsplit('/', 1)[-1],
            offset_bytes=info[part['name']]['start'], size_bytes=info[part['name']]['size'])
            for part in self.layout['partitions']]
        if gpt['partition_records'] != expected_records:
            raise ValueError('On-disk GPT identities disagree with the running partition map')
        output = (read_command or subprocess.check_output)(['/usr/bin/fw_printenv', '-c', str(self.env_config),
            'sv08_env_layout', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT'], text=True)
        lines = output.splitlines()
        if len(lines) != 4:
            raise ValueError('Unexpected environment response')
        validate_environment(dict(line.split('=', 1) for line in lines), environment['layout_id'])
        validate_status(self.status(read_command), self.manifest, self.policy, boot)
        mounted = {line.split()[2] for line in Path('/proc/self/mountinfo').read_text().splitlines()}
        other = 'b' if boot['slot'] == 'A' else 'a'
        if any(info[kind+'-'+other]['number'] in mounted for kind in ('boot', 'root')):
            raise ValueError('Inactive target filesystem is mounted')
        self.boot = dict(boot)

    def cleanup_observation(self, boot, lease_fd):
        """Bound only new read-only cleanup probes; install duration is unchanged.

        Retains the existing immutable/identified backend context requirement.
        """
        import time
        from sv08_bundle import manifest_output
        deadline = time.monotonic()+CLEANUP_SECONDS
        def read(command, **kwargs):
            remaining = deadline-time.monotonic()
            if remaining <= 0: raise ValueError('Cleanup backend observation timed out')
            return manifest_output(command, lease_fd=lease_fd, seconds=remaining).decode()
        self.validate_context(boot, read_command=read)
        status = self.status(read)
        slots = {name: value for item in status['slots'] for name, value in item.items()}
        return dict(primary={'rootfs.0':'A', 'rootfs.1':'B', None:None}[status['boot_primary']],
                    good={slot:slots['rootfs.'+str(index)]['boot_status']=='good' for index,slot in enumerate(('A','B'))})

    def primary(self):
        return {'rootfs.0': 'A', 'rootfs.1': 'B', None: None}[self.status()['boot_primary']]

    def good(self, slot):
        slots = {name: value for item in self.status()['slots'] for name, value in item.items()}
        return slots['rootfs.'+str(('A', 'B').index(slot))]['boot_status'] == 'good'

    def mark(self, action, slot):
        if self.boot is None:
            raise ValueError('Validate the running context before bootloader writes')
        self.validate_context(self.boot)
        self.command('status', action, 'rootfs.'+str(('A', 'B').index(slot)))

    def mark_active(self, slot): self.mark('mark-active', slot)
    def mark_bad(self, slot): self.mark('mark-bad', slot)
    def mark_good(self, slot): self.mark('mark-good', slot)

    def install(self, bundle, proof, target):
        if self.boot is None or target == self.boot['slot']:
            raise ValueError('Validate the source and choose the inactive target')
        self.validate_context(self.boot)
        actual = inspect_bundle(bundle, self.policy, self.keyring)
        if actual != proof:
            raise ValueError('Staged file or signed admission proof changed')
        source = self.boot['slot'].lower()
        sizes = {'boot': self.policy['image_bytes']['boot'], 'root': self.policy['image_bytes']['rootfs']}
        devices = self.manifest['devices']
        before = {kind: digest_device(devices[kind+'-'+source], size) for kind, size in sizes.items()}
        self.command('install', str(bundle))
        for kind, size in sizes.items():
            if digest_device(devices[kind+'-'+source], size) != before[kind]:
                raise ValueError('Active slot changed during installation')
            expected = proof['image_hashes']['rootfs' if kind == 'root' else 'boot']
            if digest_device(devices[kind+'-'+target.lower()], size) != expected:
                raise ValueError('Inactive image does not match the authenticated digest')
