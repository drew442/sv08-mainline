from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_package import require_writable, SERVICES


class PackagePolicyTests(unittest.TestCase):
    def test_running_starting_or_unknown_printer_blocks_package_change(self):
        for active in ('active', 'activating', 'deactivating', 'unknown'):
            with self.assertRaises(ValueError):
                require_writable({'mode':'writable'}, {'requested_mode':'writable','pending':None}, {s:active for s in SERVICES})

    def test_both_policy_and_actual_mode_must_be_writable(self):
        services = {s:'inactive' for s in SERVICES}
        for boot, wanted in [('immutable','writable'),('writable','immutable')]:
            with self.assertRaises(ValueError):
                require_writable({'mode':boot}, {'requested_mode':wanted,'pending':None}, services)
        require_writable({'mode':'writable'}, {'requested_mode':'writable','pending':None}, services)
        with self.assertRaises(ValueError):
            require_writable({'mode':'writable'}, {'requested_mode':'writable','pending':{'slot':'B'}}, services)
