"""The running-host command must remain inspection-only without --execute."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from scripts import live_h616_recovery_stage as live
from tests.sv08_emmc_job import canonical_json
from tests.test_h616_reimage_candidate import synthetic_policy


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


if __name__ == '__main__':
    unittest.main()
