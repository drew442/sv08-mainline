"""Offline checks for the explicit SD trusted-initramfs composition boundary."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts import build_sd_network_image as sd
from scripts.build_h616_reimage_candidate import build as build_h616
from scripts.ed25519_build import ED25519_SOURCES
from tests.test_h616_reimage_candidate import signed_inputs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TrustedWriterCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (sd.REPO / 'local').mkdir(mode=0o700, exist_ok=True)

    def bundle(self, root, source='192.0.2.10:/exports/exact'):
        root.mkdir()
        content = {
            'sd-network-init': b'synthetic-writer',
            'job.json': b'job', 'job.sig': b'signature',
            'commissioning-target-policy.json':
                json.dumps({'image_sha256': 'a' * 64}).encode(),
            'expected.sha256': ('a' * 64 + '\n').encode(),
        }
        for name, data in content.items():
            (root / name).write_bytes(data)
        manifest = {
            'mode': 'h616-commissioning',
            'status': 'nondeployable-commissioning-candidate',
            'bootable_sd_image': False, 'claim_trigger_provisioned': False,
            'trusted_initramfs': True, 'image_nfs_source': source,
            'binary_sha256': sha(root / 'sd-network-init'),
            'job_sha256': sha(root / 'job.json'),
            'signature_sha256': sha(root / 'job.sig'),
            'policy_sha256': sha(root / 'commissioning-target-policy.json'),
        }
        (root / 'reimage-manifest.json').write_text(json.dumps(manifest))
        return root

    def test_default_script_stays_diagnostic_and_commissioning_parameters_are_bounded(self):
        hashes = {'Image': 'a' * 64, 'initrd.img': 'b' * 64, 'sv08.dtb': 'c' * 64}
        default = sd.boot_script('192.0.2.10', '/exports/exact', hashes)
        self.assertIn('init=/sd-network-init"', default)
        self.assertNotIn('sv08.h616_commissioning', default)
        commissioning = sd.boot_script('192.0.2.10', '/exports/exact', hashes,
                                       claim_port=12345)
        self.assertIn('sv08.h616_commissioning=1 sv08.claim_port=12345', commissioning)
        self.assertIn('root=/dev/ram0 boot=nfs ro ip=dhcp', commissioning)
        self.assertIn('rdinit=/init', commissioning)
        self.assertNotIn('root=/dev/nfs', commissioning)
        self.assertNotIn('init=/sd-network-init', commissioning)
        self.assertIn('hash -v sha256', commissioning)

    def test_exact_bundle_and_initramfs_overlay(self):
        with tempfile.TemporaryDirectory(dir=sd.REPO / 'local') as temporary:
            work = Path(temporary)
            root = self.bundle(work / 'bundle')
            bundle = sd.commissioning_bundle(root, '192.0.2.10', '/exports/exact')
            initrd = work / 'initrd.img'
            base = work / 'base'
            (base / 'scripts/init-bottom').mkdir(parents=True)
            (base / 'init').write_text('#!/bin/sh\nrun_scripts /scripts/init-bottom\n')
            (base / 'scripts/functions').write_text('run_scripts() { initdir=$1; . "${initdir}/ORDER"; }\n')
            (base / 'scripts/nfs').write_text('# NFS setup fixture\n')
            (base / 'scripts/init-bottom/ORDER').write_text('/scripts/init-bottom/udev "$@"\n')
            archive = work / 'base.cpio'
            with archive.open('wb') as out:
                subprocess.run(['cpio', '--quiet', '-o', '-H', 'newc'], cwd=base,
                               input=b'.\ninit\nscripts\nscripts/functions\nscripts/nfs\nscripts/init-bottom\n'
                                     b'scripts/init-bottom/ORDER\n', stdout=out, check=True)
            with initrd.open('wb') as out:
                subprocess.run(['gzip', '-n', '-c', archive], stdout=out, check=True)
            receipt = sd.append_commissioning_initramfs(
                initrd, bundle, '192.0.2.10', '/exports/exact', work)
            self.assertEqual(receipt['source_mount'], '/root')
            self.assertEqual(receipt['writer_sha256'], sha(root / 'sd-network-init'))
            listing = subprocess.check_output(['cpio', '-it', '--quiet'],
                                              input=(work / 'commissioning.cpio').read_bytes(),
                                              text=False).decode()
            self.assertIn('scripts/init-bottom/ORDER', listing)
            order = (work / 'commissioning-initramfs/scripts/init-bottom/ORDER').read_text()
            self.assertIn('exec /trusted-writer', order)
            self.assertIn('while :; do sleep 3600; done', order)
            self.assertNotIn('switch_root', order)
            unpack = work / 'unpacked'
            sd.run('unmkinitramfs', initrd, unpack)
            self.assertEqual((unpack / 'scripts/init-bottom/ORDER').read_text(), order)
            self.assertEqual((unpack / 'trusted-writer').read_bytes(), b'synthetic-writer')
            fixture = root / 'synthetic-mmc'
            fixture.mkdir()
            (fixture / 'cid').write_text('synthetic-only\n')
            with self.assertRaisesRegex(ValueError, 'forbidden in a physical bundle'):
                sd.commissioning_bundle(root, '192.0.2.10', '/exports/exact')
            (fixture / 'cid').unlink()
            fixture.rmdir()
            again = work / 'again'
            again.mkdir()
            second = again / 'initrd.img'
            with second.open('wb') as out:
                subprocess.run(['gzip', '-n', '-c', archive], stdout=out, check=True)
            duplicate = sd.append_commissioning_initramfs(
                second, bundle, '192.0.2.10', '/exports/exact', again)
            self.assertEqual(receipt['initramfs_sha256'], duplicate['initramfs_sha256'])
            with self.assertRaisesRegex(ValueError, 'inert H616'):
                sd.commissioning_bundle(root, '192.0.2.11', '/exports/exact')
            (root / 'job.sig').write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                sd.commissioning_bundle(root, '192.0.2.10', '/exports/exact')
            (root / 'job.sig').unlink()
            (root / 'job.sig').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, 'links'):
                sd.commissioning_bundle(root, '192.0.2.10', '/exports/exact')

    def test_writer_guards_mount_before_target_open(self):
        source = (sd.REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c').read_text()
        body = source[source.index('#else\nint main(void) {', source.index('SV08_CHALLENGE_SELFTEST')):]
        self.assertLess(body.index('trusted_image_mount()'), body.index('claim_once(cmd,descriptor_hash)'))
        self.assertLess(body.rindex('trusted_image_mount()'), body.index('out=open(target,O_RDWR'))
        self.assertIn('!strcmp(src,SV08_IMAGE_NFS_SOURCE)', source)
        self.assertIn('fstatvfs(in,&source_fs)', source)

    def test_exact_read_only_nfs_mount_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / 'mount-check'
            subprocess.run([
                'cc', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                '-DSV08_H616_TRUSTED_INITRAMFS=1',
                '-DSV08_IMAGE_NFS_SOURCE="192.0.2.10:/exports/exact"',
                '-DSV08_TRUSTED_MOUNT_SELFTEST=1',
                '-I' + str(sd.REPO / 'upstream/monocypher/src'),
                '-I' + str(sd.REPO / 'upstream/monocypher/src/optional'),
                '-o', str(binary),
                str(sd.REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c'),
                *(str(path) for path in ED25519_SOURCES)],
                check=True, capture_output=True)
            cases = {
                'right': ('192.0.2.10:/exports/exact /root nfs ro,vers=3 0 0\n', 'admitted'),
                'wrong export': ('192.0.2.10:/exports/other /root nfs ro 0 0\n', 'refused'),
                'wrong server': ('192.0.2.11:/exports/exact /root nfs ro 0 0\n', 'refused'),
                'writable': ('192.0.2.10:/exports/exact /root nfs rw 0 0\n', 'refused'),
                'missing': ('tmpfs /tmp tmpfs rw 0 0\n', 'refused'),
                'duplicate': ('192.0.2.10:/exports/exact /root nfs ro 0 0\n' * 2,
                              'refused'),
            }
            for name, (records, expected) in cases.items():
                with self.subTest(case=name):
                    mount_file = root / 'mounts'
                    mount_file.write_text(records)
                    self.assertEqual(subprocess.check_output(
                        [str(binary), str(mount_file)], text=True).strip(), expected)

    def test_synthetic_h616_bundle_binds_exact_nfs_source(self):
        with tempfile.TemporaryDirectory(dir=sd.REPO / 'local') as temporary:
            work = Path(temporary)
            files, _, _ = signed_inputs(work)
            manifest = build_h616(
                work / 'bundle', *files.values(), now=1500, synthetic_test=True,
                trusted_initramfs=True, source_server='10.0.2.2',
                source_export='/exports/exact')
            self.assertTrue(manifest['trusted_initramfs'])
            self.assertEqual(manifest['image_nfs_source'], '10.0.2.2:/exports/exact')
            sd.commissioning_bundle(work / 'bundle', '10.0.2.2', '/exports/exact')
            with self.assertRaisesRegex(ValueError, 'inert H616'):
                sd.commissioning_bundle(work / 'bundle', '10.0.2.2', '/exports/other')


if __name__ == '__main__':
    unittest.main()
