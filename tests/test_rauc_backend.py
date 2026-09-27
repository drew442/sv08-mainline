import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'runtime'))
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
