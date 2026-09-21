import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).with_name("recovery_export_vm.py")
SPEC = importlib.util.spec_from_file_location("recovery_export_vm", PATH)
vm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vm)


class RecoveryExportVMTests(unittest.TestCase):
    def test_profile_is_complete_and_uses_only_measured_identities(self):
        profile = vm.reviewed_profile()
        self.assertEqual(set(profile), {"recovery", "source", "source_path", "media",
                                        "protected", "destinations"})
        self.assertEqual([item["role"] for item in profile["protected"]],
                         ["slot-a", "slot-b", "additional-protected"])
        self.assertEqual([item["stable"] for item in profile["media"]],
                         sorted((item["stable"] for item in profile["media"]),
                                key=lambda value: json.dumps(value, sort_keys=True,
                                                             separators=(",", ":"))))
        self.assertEqual(profile["recovery"]["stable"], {"serial": "SV08-RECOVERY"})
        self.assertEqual(profile["source"]["stable"],
                         {"device/wwid": "naa.5000000000000001"})
        self.assertTrue(profile["media"][-1]["removable"] or
                        any(item["removable"] for item in profile["media"]))

    def test_qemu_is_offline_and_binds_both_manifests(self):
        command = [str(item) for item in vm.qemu_command(Path("/candidate"), Path("/fixture"),
                                                         Path("/qmp"), "a" * 64, "b" * 64)]
        joined = " ".join(command)
        self.assertIn("sv08.envelope=" + "a" * 64, joined)
        self.assertIn("sv08.recovery=" + "b" * 64, joined)
        self.assertIn("-nic none", joined)
        self.assertNotIn("-netdev", command)
        self.assertNotIn("virtfs", joined)
        self.assertIn("readonly=on", joined)
        self.assertIn("removable=on", joined)
        self.assertIn("wwn=0x5000000000000003", joined)

    def test_output_guard_refuses_paths_outside_owned_prefix(self):
        with self.assertRaises(ValueError):
            vm.safe_regular(Path(tempfile.gettempdir()) / "other")


if __name__ == "__main__":
    unittest.main()
