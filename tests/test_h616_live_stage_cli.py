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
        cls.fixtures = [purpose_artifact(cls.root / name, preflight_only=mode)
                        for name, mode in [('preflight', True), ('write', False)]]

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


if __name__ == '__main__':
    unittest.main()
