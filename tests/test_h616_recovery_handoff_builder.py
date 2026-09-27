"""Offline artifact composition check for the recovery RAM-writer handoff."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.build_h616_reimage_candidate import build as build_writer
from scripts.build_h616_recovery_handoff import build as build_handoff
from tests.test_h616_reimage_candidate import signed_inputs


REPO = Path(__file__).resolve().parents[1]


def base_initrd(work):
    root = work / 'base'
    (root / 'scripts/init-bottom').mkdir(parents=True)
    (root / 'init').write_text('#!/bin/sh\nrun_scripts /scripts/init-bottom\n')
    (root / 'scripts/functions').write_text(
        'run_scripts() { initdir=$1; . "${initdir}/ORDER"; }\n')
    (root / 'scripts/nfs').write_text('# offline NFS fixture\n')
    (root / 'scripts/init-bottom/ORDER').write_text('/scripts/init-bottom/udev "$@"\n')
    archive = work / 'base.cpio'
    with archive.open('wb') as stream:
        subprocess.run(['cpio', '--quiet', '-o', '-H', 'newc'], cwd=root,
                       input=b'.\ninit\nscripts\nscripts/functions\nscripts/nfs\n'
                             b'scripts/init-bottom\nscripts/init-bottom/ORDER\n',
                       stdout=stream, check=True)
    result = work / 'base-initrd.img'
    with result.open('wb') as stream:
        subprocess.run(['gzip', '-n', '-c', archive], stdout=stream, check=True)
    return result


class RecoveryHandoffBuilderTests(unittest.TestCase):
    def test_signed_bundle_becomes_bounded_fit_and_recovery_fallback(self):
        (REPO / 'local').mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary)
            files, _, job = signed_inputs(work)
            bundle = work / 'bundle'
            build_writer(bundle, *files.values(), now=1500, synthetic_test=True,
                         trusted_initramfs=True, recovery_handoff=True,
                         source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs')
            kernel = work / 'Image'
            kernel.write_bytes(b'K' * 4096)
            dtb = work / 'board.dtb'
            dtb.write_bytes(b'D' * 512)
            initrd = base_initrd(work)
            result = build_handoff(work / 'handoff', kernel, initrd,
                                   dtb, bundle, '10.0.2.2', '/srv/sv08-sd-nfs', 12345)
            root = work / 'handoff'
            self.assertEqual(result['status'], 'nondeployable-offline-candidate')
            self.assertEqual(result['job_id'], job['job_id'])
            self.assertLess(result['fit_bytes'], 64 * 1024 * 1024)
            self.assertEqual((root / 'armed').read_bytes(), b'SV08-REIMAGE-ONCE\n')
            script = (root / 'recovery.cmd').read_text()
            self.assertIn(f'sv08_reimage_arm}}" = "{job["job_id"]}"', script)
            self.assertIn('crc32 -v', script)
            self.assertIn('iminfo 0x48000000', script)
            self.assertIn('bootm 0x48000000', script)
            self.assertIn('sv08-reimage/recovery-original.scr', script)
            self.assertIn('sv08.h616_recovery_handoff=1', result['bootargs'])
            for name, expected in result['files_sha256'].items():
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected)
            self.assertIn('FIT description:', subprocess.check_output(
                ['mkimage', '-l', root / 'writer.itb'], text=True))
            with self.assertRaisesRegex(ValueError, 'Fresh non-symlink'):
                build_handoff(work / 'handoff', kernel, initrd, dtb,
                              bundle, '10.0.2.2', '/srv/sv08-sd-nfs', 12345)


if __name__ == '__main__':
    unittest.main()
