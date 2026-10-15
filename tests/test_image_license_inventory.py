# SPDX-License-Identifier: AGPL-3.0-or-later
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import image_license_inventory as m


class ImageInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name);self.image=self.base/'image.raw'
        raw=bytearray(8192);raw[1080:1082]=b'\x53\xef';self.image.write_bytes(raw)

    def test_real_bytes_raw_and_dos_partition_hashes_and_truncation(self):
        self.assertEqual(m.geometry(self.image)[0]['size_bytes'],8192)
        raw=bytearray(8192);raw[510:512]=b'\x55\xaa'
        raw[450]=0x83;struct.pack_into('<II',raw,454,2,4);self.image.write_bytes(raw)
        part=m.geometry(self.image)[0]
        self.assertEqual((part['offset_bytes'],part['size_bytes']),(1024,2048))
        self.assertEqual(m.file_hash(self.image,1024,2048),m.hashlib.sha256(bytes(2048)).hexdigest())
        struct.pack_into('<II',raw,454,2,100);self.image.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'truncated'):m.geometry(self.image)
        with self.assertRaisesRegex(ValueError,'Truncated'):m.file_hash(self.image,0,9000)

    def test_filesystem_hash_uses_superblock_size_separately_from_partition_padding(self):
        raw=bytearray(self.image.read_bytes());struct.pack_into('<I',raw,1028,4);self.image.write_bytes(raw)
        part=m.geometry(self.image)[0];filesystem=m.filesystem_identity(self.image,part)
        self.assertEqual(filesystem['bytes'],4096)
        self.assertEqual(filesystem['sha256'],m.file_hash(self.image,0,4096))
        self.assertNotEqual(filesystem['sha256'],m.file_hash(self.image))
        struct.pack_into('<I',raw,1028,100);self.image.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'Truncated'):m.filesystem_identity(self.image,part)

    def test_missing_unsafe_and_unsupported_images(self):
        link=self.base/'link';link.symlink_to(self.image)
        with self.assertRaises(ValueError):m.geometry(link)
        with self.assertRaises(OSError):m.geometry(self.base/'missing')
        self.image.write_bytes(b'broken')
        with self.assertRaises(ValueError):m.geometry(self.image)

    def mount_data(self):
        return [{'filesystems':[dict(target=str(self.base),source='/dev/loop9',fstype='ext4',options='ro,norecovery')]},
                {'loopdevices':[{'name':'/dev/loop9','back-file':str(self.image),'offset':0,'sizelimit':8192,'ro':True}]}]

    def test_mount_requires_kernel_ro_nojournal_exact_artifact_and_offset(self):
        for change in ('rw','journal','backing','offset','loop_rw','ordinary-directory'):
            with self.subTest(change=change):
                data=self.mount_data()
                if change=='rw':data[0]['filesystems'][0]['options']='rw,norecovery'
                if change=='journal':data[0]['filesystems'][0]['options']='ro'
                if change=='backing':data[1]['loopdevices'][0]['back-file']='/another'
                if change=='offset':data[1]['loopdevices'][0]['offset']=512
                if change=='loop_rw':data[1]['loopdevices'][0]['ro']=False
                if change=='ordinary-directory':data[0]['filesystems'][0]['target']='/'
                with patch.object(m,'command_json',side_effect=data),self.assertRaises(ValueError):
                    m.verified_mount(self.base,self.image,0,8192,'ext4')
        with patch.object(m,'command_json',side_effect=self.mount_data()):
            self.assertTrue(m.verified_mount(self.base,self.image,0,8192,'ext4')['read_only'])

    def test_only_software_bytes_no_secret_or_data_read_and_symlink_escape(self):
        for path,content in [('usr/bin/app',b'app'),('bin/busybox',b'busybox'),('etc/shadow',b'secret'),('data/token',b'token')]:
            target=self.base/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        (self.base/'usr/escape').symlink_to('/etc/shadow')
        hashed=[];original=m.file_hash
        def capture(path,*args):hashed.append(str(path));return original(path,*args)
        with patch.object(m,'file_hash',side_effect=capture):records=m.tree_inventory(self.base)
        self.assertEqual(set(hashed),{str(self.base/'usr/bin/app'),str(self.base/'bin/busybox')})
        self.assertEqual({r['path'] for r in records},{'usr/bin/app','usr/escape','bin/busybox'})
        with self.assertRaises(ValueError):m.safe_file(self.base,'usr/escape')

    def test_missing_package_database_is_explicit_unknown_input(self):
        self.assertEqual(m.installed_packages(self.base),[])

    def test_actual_dpkg_status_versions_not_baseline_and_notice_tamper(self):
        status=self.base/'var/lib/dpkg/status';status.parent.mkdir(parents=True)
        status.write_text('Package: example\nStatus: install ok installed\nVersion: 2.3\nArchitecture: arm64\n\nPackage: removed\nStatus: deinstall ok config-files\n')
        notice=self.base/'usr/share/doc/example/copyright';notice.parent.mkdir(parents=True);notice.write_text('supplier')
        first=m.installed_packages(self.base)
        self.assertEqual([(p['name'],p['version']) for p in first],[('example','2.3')])
        notice.write_text('changed');self.assertNotEqual(first,m.installed_packages(self.base))
        notice.unlink();self.assertEqual(m.installed_packages(self.base)[0]['notice_status'],'missing')

    def test_managed_mount_cleanup_on_check_failure_and_no_writes(self):
        calls=[]
        def run(args,**kwargs):calls.append(args)
        with patch.object(m.subprocess,'check_output',return_value='/dev/loop9\n'),patch.object(m.subprocess,'run',side_effect=run),patch.object(m,'verified_mount'):
            with self.assertRaisesRegex(ValueError,'check failed'):
                with m.mounted_image(self.image,m.geometry(self.image)[0],self.base):raise ValueError('check failed')
        self.assertEqual(calls[-2][0],'umount');self.assertEqual(calls[-1],['losetup','--detach','/dev/loop9'])
        self.assertIn('ro,noload',calls[0]);self.assertEqual(self.image.stat().st_size,8192)

    def test_gpt_reuses_validated_upstream_parser(self):
        raw=bytearray(8192);raw[510:512]=b'\x55\xaa';raw[512:520]=b'EFI PART';self.image.write_bytes(raw)
        with patch.object(m,'inspect_gpt',return_value={'partition_records':[{'number':2}]}) as inspect:
            self.assertEqual(m.geometry(self.image),[{'number':2}]);inspect.assert_called_once_with(self.image)

if __name__=='__main__':unittest.main()
