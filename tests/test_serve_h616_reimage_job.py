"""Offline controller checks; never start NFS or write an eMMC."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_h616_reimage_job import LOCAL
from scripts.serve_h616_reimage_job import ganesha_config, serve


class ServeJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LOCAL.mkdir(mode=0o700, exist_ok=True)

    def test_export_is_read_only_for_one_client(self):
        with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
            root = Path(temporary)
            config = ganesha_config(export_dir=root / 'export', pseudo='/srv/sv08-sd-nfs',
                                    bind='192.168.1.20', printer_ip='192.168.1.141',
                                    recovery_dir=root / 'recovery')
            self.assertIn('Access_Type = NONE;', config)
            self.assertIn('Clients = 192.168.1.141; Access_Type = RO;', config)
            self.assertIn('Squash = Root_Squash;', config)
            self.assertNotIn('Access_Type = RW;', config)
            for bad in ('127.0.0.1', '192.168.1.20', '192.168.1.0/24'):
                with self.assertRaises(ValueError):
                    ganesha_config(export_dir=root / 'export', pseudo='/srv/sv08-sd-nfs',
                                   bind='192.168.1.20', printer_ip=bad,
                                   recovery_dir=root / 'recovery')

    def test_dry_run_does_not_create_export_or_start_listener(self):
        LOCAL.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
            root = Path(temporary)
            state = root / 'state'
            state.mkdir()
            (state / 'state.json').write_text(json.dumps({
                'source_server': '192.168.1.20', 'source_export': '/srv/sv08-sd-nfs',
                'image_sha256': 'a' * 64, 'claim_port': 18080,
            }))
            image = root / 'image.bin'
            image.write_bytes(b'not a real image')
            image.chmod(0o644)
            executable = root / 'service'
            executable.write_bytes(b'#!/bin/sh\n')
            executable.chmod(0o755)
            export = root / 'export'
            report = serve(state_dir=state, image=image,
                           job_verification_key=root / 'job.pub',
                           receipt_signing_key=root / 'receipt.key', export_dir=export,
                           printer_ip='192.168.1.141', rpcbind=executable,
                           ganesha=executable)
            self.assertEqual(report['status'], 'inspection-only')
            self.assertEqual(len(report['ganesha_sha256']), 64)
            self.assertEqual(report['ganesha_sha256'], report['rpcbind_sha256'])
            self.assertFalse(export.exists())
            self.assertFalse((state / 'serve-start.json').exists())
            root.chmod(0o755)
            with self.assertRaisesRegex(ValueError, 'private 0700 parent'):
                serve(state_dir=state, image=image,
                      job_verification_key=root / 'job.pub',
                      receipt_signing_key=root / 'receipt.key', export_dir=export,
                      printer_ip='192.168.1.141', rpcbind=executable,
                      ganesha=executable)


if __name__ == '__main__':
    unittest.main()
