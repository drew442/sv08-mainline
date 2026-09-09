from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from measure_host_slot import check_source


class SlotSourceTests(unittest.TestCase):
    def test_nested_mount_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(Path, 'read_text', return_value=f'1 0 0:0 / {root}/proc rw - proc proc rw\n'):
                with self.assertRaisesRegex(ValueError, 'Unmount'):
                    check_source(root)

    def test_symlink_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / 'root'
            link.symlink_to(tmp)
            with self.assertRaises(ValueError):
                check_source(link)
