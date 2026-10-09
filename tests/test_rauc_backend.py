import copy
from contextlib import nullcontext
import os
import stat
from types import SimpleNamespace
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'runtime'))
from sv08_rauc_bootloader import handle
from sv08_rauc import Backend, SLOT_NAMES, validate_config, validate_environment, validate_geometry, validate_status


class BackendPolicyTests(unittest.TestCase):
    def setUp(self):
        self.layout = json.loads((REPO/'configs/images/host-ab.json').read_text())
        self.policy = dict(compatible='test-profile', layout='ab-8gb-v1',
                           image_bytes={'boot': 192*1024**2, 'rootfs': 2048*1024**2})
        self.manifest = {'devices': {part['name']: '/explicit/'+part['name'] for part in self.layout['partitions']}}
        self.boot = {'slot': 'A'}
        text = (REPO/'configs/host-os/rauc-system.conf.in').read_text()
        for placeholder, value in {'COMPATIBLE': 'test-profile', 'ROOT_A': '/explicit/root-a',
            'ROOT_B': '/explicit/root-b', 'BOOT_A': '/explicit/boot-a', 'BOOT_B': '/explicit/boot-b'}.items():
            text = text.replace('@'+placeholder+'@', value)
        self.text = text
        offset = 16*1024**2; self.info = {}
        for index, part in enumerate(self.layout['partitions'], 1):
            size = part['mib']*1024**2
            self.info[part['name']] = dict(partition=index, number=f'254:{index}', parent=Path('/sys/fake/disk'), size=size, start=offset)
            offset += size
        self.status = dict(compatible='test-profile', booted='A', variant=None, slots=[])
        for name, (role, kind, bootname, parent) in SLOT_NAMES.items():
            active = role.endswith('a')
            state = ('booted' if bootname else 'active') if active else 'inactive'
            self.status['slots'].append({name: dict(device=self.manifest['devices'][role],
                type=kind, bootname=bootname, parent=parent, state=state, mountpoint=None,
                **{'class': name.split('.')[0]})})

    def test_reviewed_pair_and_geometry_pass(self):
        validate_config(self.text, self.manifest, self.policy, '/etc/rauc/release-keyring.pem')
        validate_status(self.status, self.manifest, self.policy, self.boot)
        self.assertEqual(validate_geometry(self.info, self.layout, self.policy), Path('/sys/fake/disk'))

    def test_auto_activation_custom_handler_wrong_device_or_keyring_refused(self):
        for text in [self.text.replace('activate-installed=false', 'activate-installed=true'),
                     self.text.replace('/usr/lib/sv08/sv08_rauc_bootloader.py', '/unexpected'),
                     self.text+'\n[unexpected]\nkey=value\n',
                     self.text.replace('/explicit/root-b', '/wrong/device'),
                     self.text.replace('parent=rootfs.1', 'parent=rootfs.0'),
                     self.text.replace('/etc/rauc/release-keyring.pem', '/wrong/keyring')]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_config(text, self.manifest, self.policy, '/etc/rauc/release-keyring.pem')

    def test_service_must_match_config_and_running_slot(self):
        for field, value in [('device', '/wrong'), ('parent', 'rootfs.0'), ('state', 'active'), ('mountpoint', '/mnt')]:
            status = copy.deepcopy(self.status)
            status['slots'][-1]['boot.1'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_status(status, self.manifest, self.policy, self.boot)
        status = copy.deepcopy(self.status); status['slots'].append(status['slots'][0])
        with self.assertRaises(ValueError): validate_status(status, self.manifest, self.policy, self.boot)
        with self.assertRaises(ValueError): validate_status(self.status, self.manifest, self.policy, {'slot': 'B'})

    def test_shifted_partition_alias_other_device_and_short_image_policy_refused(self):
        for field, value in [('start', 4*1024**2), ('size', 1), ('number', '254:2'),
                             ('parent', Path('/sys/other/disk')), ('partition', 2)]:
            info = copy.deepcopy(self.info); info['boot-a'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_geometry(info, self.layout, self.policy)
        policy = copy.deepcopy(self.policy); policy['image_bytes']['rootfs'] -= 4096
        with self.assertRaises(ValueError): validate_geometry(self.info, self.layout, policy)

    def test_environment_counters_match_bounded_boot_policy(self):
        values = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='B A', BOOT_A_LEFT='3', BOOT_B_LEFT='0')
        validate_environment(values, 'ab-8gb-v1')  # A currently running final B attempt is valid.
        for name, bad in [('BOOT_ORDER', 'A A'), ('BOOT_ORDER', ''), ('BOOT_A_LEFT', '4'),
                          ('BOOT_B_LEFT', '-1'), ('sv08_env_layout', 'other')]:
            with self.subTest(name=name, bad=bad), self.assertRaises(ValueError):
                validate_environment(dict(values, **{name: bad}), 'ab-8gb-v1')

    def normal_backend(self, values):
        backend = object.__new__(Backend)
        backend.env_config = Path('/reviewed/fw_env.config')
        backend.environment = {'layout_id': 'ab-8gb-v1'}
        backend.writer = nullcontext
        backend.operation = lambda *_: nullcontext()
        backend.boot_policy = lambda: dict(values)
        backend.normal_resolution_evidence = Mock(side_effect=lambda boot:
            dict(bus='bus', owner=':1.42', identity={'files': {'config': 'hash'}},
                 slot_status_sha256=values['BOOT_A_LEFT']))
        writes = []
        def command(*args):
            slot = ('A', 'B')[int(args[2].split('.')[1])]
            def write(name, value):
                writes.append((name, value)); values[name] = value
            return handle(['set-state', slot, 'good'], read=lambda: dict(values), write=write,
                          operation=lambda: dict(action='set-good', slot=slot),
                          running=lambda: slot, verify_copies=lambda: None)
        backend.command = command
        return backend, writes

    def test_normal_confirmation_uses_counter_only_handler_on_current_final_attempt(self):
        for slot, order in [('A', 'A B'), ('B', 'B A'), ('A', 'B A'), ('A', 'A')]:
            with self.subTest(slot=slot, order=order):
                values = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER=order,
                              BOOT_A_LEFT='0', BOOT_B_LEFT='0')
                other = 'B' if slot == 'A' else 'A'
                values['BOOT_'+other+'_LEFT'] = '0' if order == 'A' else '2'
                before = dict(values)
                backend, writes = self.normal_backend(values)
                with patch('sv08_rauc.verify_environment_copies') as verify, \
                     patch('sv08_rauc_bootloader.os.geteuid', return_value=0):
                    backend.confirm_normal(dict(slot=slot, trial=False))
                self.assertEqual(writes, [('BOOT_'+slot+'_LEFT', '3')])
                self.assertEqual(values, dict(before, **{'BOOT_'+slot+'_LEFT': '3'}))
                self.assertEqual(verify.call_count, 2)

    def test_normal_confirmation_refuses_trial_absent_slot_and_corrupt_redundancy(self):
        for trial, order, corrupt in [(True, 'A B', False), (False, 'B', False), (False, 'A B', True)]:
            with self.subTest(trial=trial, order=order, corrupt=corrupt):
                values = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER=order, BOOT_A_LEFT='0', BOOT_B_LEFT='2')
                backend, writes = self.normal_backend(values)
                with patch('sv08_rauc.verify_environment_copies', side_effect=ValueError('CRC') if corrupt else None):
                    with self.assertRaises(ValueError):
                        backend.confirm_normal(dict(slot='A', trial=trial))
                self.assertEqual(writes, [])

    def test_normal_confirmation_detects_other_counter_order_and_identity_changes(self):
        for changed in ('order', 'other', 'identity'):
            with self.subTest(changed=changed):
                values = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B', BOOT_A_LEFT='0', BOOT_B_LEFT='2')
                backend, writes = self.normal_backend(values)
                original = backend.command
                def command(*args):
                    original(*args)
                    if changed == 'order': values['BOOT_ORDER'] = 'B A'
                    if changed == 'other': values['BOOT_B_LEFT'] = '1'
                    if changed == 'identity':
                        backend.normal_resolution_evidence = lambda boot: dict(owner='changed')
                backend.command = command
                with patch('sv08_rauc.verify_environment_copies'), patch('sv08_rauc_bootloader.os.geteuid', return_value=0):
                    with self.assertRaisesRegex(ValueError, 'changed boot policy or running context'):
                        backend.confirm_normal(dict(slot='A', trial=False))

    def test_complete_writable_context_checks_devices_boot_mount_and_skips_printing_pin(self):
        manifest = dict(self.manifest, deployable=True, release='release-1', state_schema=1)
        policy = dict(self.policy, state_schema=1)
        environment = dict(layout_id='ab-8gb-v1', medium='mmc-user-area', size_bytes=65536,
                           copy_offsets_bytes=[4*1024**2, 8*1024**2], board_mmc_device_index=1)
        backend = Backend(manifest, policy, self.layout, environment)
        backend.config = Mock(); backend.config.read_text.return_value = self.text
        backend.env_config = Mock(); backend.env_config.read_text.return_value = '/dev/reviewed 0x400000 0x10000\n/dev/reviewed 0x800000 0x10000\n'
        boot = dict(slot='A', mode='writable', release='release-1', trial=False, customized=True)
        records = [dict(number=self.info[part['name']]['partition'], name=part['name'],
                        partuuid=manifest['devices'][part['name']].rsplit('/', 1)[-1],
                        offset_bytes=self.info[part['name']]['start'], size_bytes=self.info[part['name']]['size'])
                   for part in self.layout['partitions']]
        def read_text(path):
            mapping = {'/sys/fake/disk/size': str(self.layout['image_bytes']//512),
                       '/sys/fake/disk/removable': '0', '/sys/fake/disk/dev': '254:0',
                       '/proc/self/mountinfo': '1 0 254:2 / / rw\n2 0 254:1 / /boot rw\n'}
            # Normal OS health must not read the host/MCU compatibility pin.
            return mapping[str(path)]
        def command(args, **_):
            if args[0] == 'findmnt': return '254:1'
            return 'sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\nBOOT_A_LEFT=0\nBOOT_B_LEFT=2\n'
        with patch('sv08_rauc.os.geteuid', return_value=0), \
             patch('sv08_rauc.os.statvfs', return_value=SimpleNamespace(f_flag=0)), \
             patch('sv08_rauc.os.stat', return_value=SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=os.makedev(254, 0))), \
             patch('sv08_rauc.Path.read_text', read_text), \
             patch('sv08_rauc.verify_devices') as devices, \
             patch('sv08_rauc.block_info', side_effect=lambda name: self.info[name.rsplit('/', 1)[-1]]), \
             patch('sv08_rauc.inspect_gpt', return_value={'partition_records': records}), \
             patch.object(backend, 'status', return_value=self.status):
            backend.validate_normal_context(boot, read_command=command)
            devices.assert_called_once_with(manifest, 'A', read_command=command)
            self.assertIsNone(backend.boot)  # Normal validation creates no image-write capability.
            with self.assertRaisesRegex(ValueError, 'immutable'):
                backend.validate_context(boot, read_command=command)
            with self.assertRaisesRegex(ValueError, 'Mounted boot'):
                backend.validate_normal_context(boot, read_command=lambda args, **kw: '254:3' if args[0] == 'findmnt' else command(args, **kw))

    def test_normal_context_does_not_authorize_image_validation_on_writable_root(self):
        backend = Backend(dict(deployable=True), dict(compatible='reviewed'), {},
                          dict(board_mmc_device_index=1))
        backend.boot = None
        with patch('sv08_rauc.os.geteuid', return_value=0), \
             patch('sv08_rauc.os.statvfs', return_value=SimpleNamespace(f_flag=0)):
            with self.assertRaisesRegex(ValueError, 'immutable running root'):
                backend.validate_context(dict(mode='writable'))
            with self.assertRaisesRegex(ValueError, 'operating mode'):
                backend.validate_normal_context(dict(mode='immutable'))
        self.assertIsNone(backend.boot)

    def test_pre_disarm_restore_refuses_when_either_raw_environment_copy_is_invalid(self):
        backend = object.__new__(Backend)
        backend.env_config = Path('/reviewed/fw_env.config')
        backend.environment = {'layout_id': 'ab-8gb-v1'}
        # verify_environment_copies validates both raw copies, rather than
        # accepting fw_printenv's preferred copy when its redundant peer fails.
        with patch('sv08_rauc.verify_environment_copies', side_effect=ValueError('bad CRC in redundant copy')) as verify, \
             patch.object(backend, 'boot_policy') as policy, \
             patch('sv08_rauc.subprocess.run') as write:
            with self.assertRaisesRegex(ValueError, 'bad CRC'):
                backend.restore_pre_disarm(
                    dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B',
                         BOOT_A_LEFT='3', BOOT_B_LEFT='3'), 'B', 'A')
        verify.assert_called_once_with(backend.env_config)
        policy.assert_not_called()
        write.assert_not_called()

    def test_pre_disarm_restore_validates_both_copies_before_and_after_each_write(self):
        backend = object.__new__(Backend)
        backend.env_config = Path('/reviewed/fw_env.config')
        backend.environment = {'layout_id': 'ab-8gb-v1'}
        previous = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B',
                        BOOT_A_LEFT='3', BOOT_B_LEFT='3')
        disarmed = dict(previous, BOOT_ORDER='A', BOOT_B_LEFT='0')
        with patch('sv08_rauc.verify_environment_copies') as verify, \
             patch.object(backend, 'primary', return_value='A'), \
             patch.object(backend, 'good', return_value=True), \
             patch.object(backend, 'boot_policy', side_effect=[disarmed, previous]), \
             patch('sv08_rauc.subprocess.run') as write:
            backend.restore_pre_disarm(previous, 'B', 'A')
        self.assertEqual([call.args[0][-2:] for call in write.call_args_list],
                         [['BOOT_B_LEFT', '3'], ['BOOT_ORDER', 'A B']])
        self.assertEqual(verify.call_count, 4)  # before, after each write, and final
        verify.assert_called_with(backend.env_config)

    def test_pre_disarm_restore_refuses_if_redundancy_breaks_during_restore(self):
        backend = object.__new__(Backend)
        backend.env_config = Path('/reviewed/fw_env.config')
        backend.environment = {'layout_id': 'ab-8gb-v1'}
        previous = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B',
                        BOOT_A_LEFT='3', BOOT_B_LEFT='3')
        disarmed = dict(previous, BOOT_ORDER='A', BOOT_B_LEFT='0')
        with patch('sv08_rauc.verify_environment_copies', side_effect=[None, ValueError('second copy CRC failed')]) as verify, \
             patch.object(backend, 'primary', return_value='A'), \
             patch.object(backend, 'good', return_value=True), \
             patch.object(backend, 'boot_policy', return_value=disarmed), \
             patch('sv08_rauc.subprocess.run') as write:
            with self.assertRaisesRegex(ValueError, 'second copy CRC'):
                backend.restore_pre_disarm(previous, 'B', 'A')
        self.assertEqual(write.call_count, 1)
        self.assertEqual(verify.call_count, 2)
