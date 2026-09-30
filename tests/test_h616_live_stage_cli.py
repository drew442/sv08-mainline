"""The running-host command must remain inspection-only without --execute."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from scripts import live_h616_recovery_stage as live
from tests.sv08_emmc_job import canonical_json
from tests.test_h616_reimage_candidate import synthetic_policy
from tests.test_recovery_handoff_stage import purpose_artifact
from scripts.build_h616_reimage_candidate import digest


class LiveStageCliTests(unittest.TestCase):
    def test_mutation_name_without_execute_only_inspects(self):
        with tempfile.TemporaryDirectory() as temporary:
            policy = Path(temporary) / 'policy.json'
            policy.write_bytes(canonical_json(synthetic_policy()))
            stdout = io.StringIO()
            with (mock.patch.object(sys, 'argv', ['live', '--operation', 'stage',
                                                  '--policy', str(policy),
                                                  '--recovery', temporary]),
                  mock.patch.object(live, 'admitted_target', return_value={
                      'cid': '0' * 32, 'target_path': '/dev/mmcblk0'}),
                  mock.patch.object(live, 'stage_mounted_recovery') as stage,
                  redirect_stdout(stdout)):
                live.main()
            stage.assert_not_called()
            self.assertEqual(json.loads(stdout.getvalue())['execute'], False)


class LivePurposeRevalidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(dir=live.REPO / 'local')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.fixtures = [purpose_artifact(cls.root / f'{name}-{v2}', preflight_only=mode, policy_v2=v2)
                        for name, mode in [('preflight', True), ('write', False)]
                        for v2 in (False, True)]

    def test_unchanged_live_stage_arm_activate_revalidate_both_purposes(self):
        for artifact, bundle, key, policy, job in self.fixtures:
            with self.subTest(purpose=job['format']):
                recovery = artifact.parent / 'live-recovery'
                recovery.mkdir()
                (recovery / 'recovery.scr').write_bytes(b'ORIGINAL-UI')
                journal = artifact.parent / 'live-journal'
                target = artifact.parent / 'nonexistent-target'
                admission = {'dev_t': policy['dev_t'], 'fixture_only': True}
                with mock.patch.object(live, 'admitted_target', return_value=admission):
                    state = live.stage_mounted_recovery(
                        recovery, artifact, journal, bundle=bundle, verification_key=key,
                        expected_build_sha256=digest((artifact / 'build.json').read_bytes()),
                        expected_original_sha256=digest(b'ORIGINAL-UI'), now=1500,
                        mounted_live_target=target, synthetic_live_fixture=True)
                    self.assertEqual(state['phase'], 'wrapper-durable')
                    real_open = os.open
                    opens = []
                    def captured_open(path, flags, *args, **kwargs):
                        if Path(path) == target:
                            opens.append(flags)
                            raise ValueError('CAPTURED_MEDIA_BOUNDARY')
                        return real_open(path, flags, *args, **kwargs)
                    for phase, operation, expected_access in (
                            ('wrapper-durable', live.arm_live_target, os.O_RDWR),
                            ('armed-both-verified', live.activate_live_target, os.O_RDONLY)):
                        state['phase'] = phase
                        (journal / 'state.json').write_text(json.dumps(state))
                        arguments = dict(target_policy=policy, artifact=artifact, bundle=bundle,
                                         verification_key=key, synthetic_fixture=True, now=1500)
                        with (mock.patch.object(live.os, 'open', side_effect=captured_open),
                              self.assertRaisesRegex(ValueError, 'CAPTURED_MEDIA_BOUNDARY')):
                            operation(target, recovery, journal, **arguments)
                        self.assertEqual(opens[-1] & os.O_ACCMODE, expected_access)
                        self.assertFalse((recovery / 'sv08-reimage/armed').exists())
                        # Later journal build pin still covers the entire mode,
                        # executable and initramfs/FIT composition.
                        state['build_sha256'] = '0' * 64
                        (journal / 'state.json').write_text(json.dumps(state))
                        before = len(opens)
                        with (mock.patch.object(live.os, 'open', side_effect=captured_open),
                              self.assertRaisesRegex(ValueError, 'changed')):
                            operation(target, recovery, journal, **arguments)
                        self.assertEqual(len(opens), before)
                        state['build_sha256'] = digest((artifact / 'build.json').read_bytes())
                        (journal / 'state.json').write_text(json.dumps(state))
                        manifest_path = bundle / 'reimage-manifest.json'
                        original = manifest_path.read_bytes()
                        manifest = json.loads(original)
                        manifest['preflight_only'] = not manifest['preflight_only']
                        manifest_path.write_text(json.dumps(manifest))
                        with (mock.patch.object(live.os, 'open', side_effect=captured_open),
                              self.assertRaisesRegex(ValueError, 'signed bundle differ')):
                            operation(target, recovery, journal, **arguments)
                        self.assertEqual(len(opens), before)
                        manifest_path.write_bytes(original)


class V2LiveCliTests(unittest.TestCase):
    def test_signed_staging_path_reaches_all_operations(self):
        from tests.test_h616_reimage_candidate import physical_v2_policy
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / 'policy'
            policy_path.write_bytes(canonical_json(physical_v2_policy()))
            for operation in ('inspect', 'stage', 'arm', 'activate'):
                with (mock.patch.object(sys, 'argv', ['live', '--operation', operation,
                          '--policy', str(policy_path), '--recovery', temporary]),
                      mock.patch.object(live, 'admitted_target', return_value={
                          'cid': '0' * 32, 'target_path': '/dev/mmcblk2'}) as admission,
                      redirect_stdout(io.StringIO())):
                    live.main()
                self.assertEqual(admission.call_args.args[0], Path('/dev/mmcblk2'))


class V2LiveAdmissionTests(unittest.TestCase):
    def test_actual_live_descriptor_card_and_p5_admission(self):
        import contextlib
        import stat
        import struct
        from tests.test_h616_reimage_candidate import physical_v2_policy, SECTORS
        for node in (0, 2):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = physical_v2_policy(node)
                host = root / '4022000.mmc/mmc_host'
                card = host / f'mmc{node}/mmc{node}:0001'
                block = card / f'block/mmcblk{node}'
                p5 = block / f'mmcblk{node}p5'
                p5.mkdir(parents=True)
                part = policy['image_layout']['partitions'][4]
                for path, value in [(card / 'type', 'MMC'), (card / 'cid', policy['cid']),
                                    (block / 'size', str(SECTORS)), (block / 'dev', '179:8'),
                                    (p5 / 'partition', '5'), (p5 / 'dev', '179:13'),
                                    (p5 / 'start', str(part['offset_bytes'] // 512)),
                                    (p5 / 'size', str(part['size_bytes'] // 512)),
                                    (p5 / 'uevent', 'PARTUUID=' + part['partuuid'])]:
                    path.write_text(value + '\n')
                classes = root / 'class'; classes.mkdir()
                (classes / p5.name).symlink_to(p5)
                recovery = root / 'recovery'; recovery.mkdir()
                target = root / f'mmcblk{node}'; target.write_bytes(b'fixture')
                source = root / 'p5'; source.write_bytes(b'fixture')
                real_stat = Path.stat
                opened_number = os.makedev(179, 8)
                def fake_stat(path, *args, **kwargs):
                    observed = real_stat(path, *args, **kwargs)
                    fields = list(observed)
                    if path in (target, source):
                        fields[0] = stat.S_IFBLK | 0o600
                        return type('DeviceStat', (), {'st_mode': fields[0],
                            'st_rdev': opened_number if path == target else os.makedev(179, 13)})()
                    if path == recovery:
                        fields[2] = os.makedev(179, 13)
                        return os.stat_result(fields)
                    return observed
                def mapped_path(value):
                    value = str(value)
                    if value == policy['target_device']: return target
                    if value == '/sys/class/block': return classes
                    return Path(value)
                fd_stat = type('FdStat', (), {'st_mode': stat.S_IFBLK,
                                              'st_rdev': opened_number})()
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(live, 'HOST_SYSFS', host))
                    stack.enter_context(mock.patch.object(live, 'Path', side_effect=mapped_path))
                    stack.enter_context(mock.patch.object(Path, 'stat', fake_stat))
                    stack.enter_context(mock.patch.object(live.os, 'fstat', return_value=fd_stat))
                    stack.enter_context(mock.patch.object(live.fcntl, 'ioctl', return_value=struct.pack('Q', SECTORS * 512)))
                    stack.enter_context(mock.patch.object(live, 'mount_record', return_value={
                        'target': str(recovery), 'source': str(source), 'fstype': 'ext4', 'options': 'rw'}))
                    gpt = stack.enter_context(mock.patch.object(live, 'inspect_gpt', return_value={
                        'disk_guid': policy['image_layout']['disk_guid'],
                        'partition_records': policy['image_layout']['partitions']}))
                    def admit(value=policy):
                        return live.admitted_target(target, recovery, value, host_sysfs=host,
                                                    local_addresses=set(), require_writable=True)
                    self.assertEqual(admit()['phase'], 'staging-host')
                    self.assertEqual(admit()['dev_t'], '179:8')
                    self.assertTrue(str(gpt.call_args.args[0]).startswith('/proc/self/fd/'))
                    expected_gpt = gpt.return_value
                    def changed_during_gpt(*args, **kwargs):
                        (block / 'dev').write_text('179:16\n')
                        return expected_gpt
                    gpt.side_effect = changed_during_gpt
                    with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                        admit()
                    (block / 'dev').write_text('179:8\n'); gpt.side_effect = None

                    for path, value in [(card / 'cid', 'f' * 32), (card / 'type', 'SD'),
                                        (block / 'dev', '179:16'), (block / 'size', str(SECTORS - 1)),
                                        (p5 / 'start', '1'), (p5 / 'size', '1'),
                                        (p5 / 'uevent', 'PARTUUID=wrong')]:
                        old = path.read_bytes(); path.write_text(value + '\n')
                        with self.subTest(node=node, path=path.name), self.assertRaises(ValueError): admit()
                        path.write_bytes(old)
                    with self.assertRaises(ValueError): admit(dict(policy, dev_t='179:16'))
                    other = card / 'block/mmcblk3'; other.mkdir()
                    with self.assertRaises(ValueError): admit()


if __name__ == '__main__':
    unittest.main()
