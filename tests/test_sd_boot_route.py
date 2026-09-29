"""Bounded real regular-file transfers; synthetic admission never admits hardware."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import sd_boot_route as route


class FixtureSD:
    def __init__(self,path):
        self.info=path.stat()
        self.calls=0
        self.changed_at=None
        self.mutate=None

    def admission(self,fd):
        self.calls+=1
        info=os.fstat(fd)
        if (info.st_dev,info.st_ino)!=(self.info.st_dev,self.info.st_ino):
            raise ValueError('Fixture device swapped')
        if self.mutate:self.mutate(fd,self.calls)
        if self.calls==self.changed_at:raise ValueError('Fixture CID/mount changed')
        return {'fixture':True,'inode':info.st_ino}

    def ranges(self,fd):
        return [(0,route.START),(2*route.CHUNK,route.CHUNK)]


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        self.device=self.work/'sd.img'
        self.device.write_bytes(b'Z'*(3*route.CHUNK))
        self.loader=self.work/'loader.bin'; self.loader.write_bytes(b'L'*80000)
        self.receipt=self.work/'prepared.json'
        self.receipt.write_text(json.dumps({'format':'sv08-managed-loader-v1',
            'loader_bytes':80000,'loader_sha256':route.sha(self.loader.read_bytes())}))
        self.preimage=self.work/'preimage';self.preimage.write_bytes(b'Z'*80000)
        self.policy={'capture_and_users_released':True,'device':str(self.device),
            'preimage_sha256':route.sha(self.preimage.read_bytes()),
            'loader_sha256':route.sha(self.loader.read_bytes()),'receipt_sha256':route.sha(self.receipt.read_bytes()),
            'capacity':self.device.stat().st_size,'ownership_lock':str(self.work/'lock')}
        self.adapter=FixtureSD(self.device)

    def transfer(self,apply=False):
        return route.transfer(self.device,self.loader,self.receipt,self.policy,self.preimage,
                              apply=apply,adapter=self.adapter)

    def test_default_is_readonly_without_preimage_file_mutation(self):
        before=self.device.read_bytes()
        with mock.patch.object(route.os,'pwrite',side_effect=AssertionError('write attempted')):
            result=self.transfer()
        self.assertFalse(result['written']);self.assertEqual(self.device.read_bytes(),before)

    def test_actual_bounded_write_preserves_all_other_bytes(self):
        before=self.device.read_bytes(); result=self.transfer(True)
        after=self.device.read_bytes()
        self.assertTrue(result['written'])
        self.assertEqual(after[:route.START],before[:route.START])
        self.assertEqual(after[route.START+80000:],before[route.START+80000:])
        self.assertEqual(after[route.START:route.START+80000],self.loader.read_bytes())
        self.assertEqual(self.adapter.calls,3)

    def test_absolute_endpoint_independent_of_partition_map(self):
        self.loader.write_bytes(b'L'*(route.LIMIT-route.START+1))
        self.receipt.write_text(json.dumps({'format':'sv08-managed-loader-v1',
            'loader_bytes':self.loader.stat().st_size,'loader_sha256':route.sha(self.loader.read_bytes())}))
        with self.assertRaises(ValueError):self.transfer(True)
        self.assertEqual(self.adapter.calls,0)

    def test_symlink_alias_and_loader_alias_refused(self):
        alias=self.work/'alias';alias.symlink_to(self.device)
        with self.assertRaises(OSError):
            route.transfer(alias,self.loader,self.receipt,{**self.policy,'device':str(alias)},self.preimage,adapter=self.adapter)
        self.loader.unlink();self.loader.symlink_to(self.device)
        with self.assertRaises(OSError):self.transfer()

    def test_loader_receipt_changed(self):
        self.loader.write_bytes(b'X'*80000)
        with self.assertRaises(ValueError):self.transfer(True)

    def test_wrong_preimage_and_retained_preimage_refuse_before_write(self):
        with mock.patch.object(route.os,'pwrite',side_effect=AssertionError('write attempted')):
            self.policy['preimage_sha256']='0'*64
            with self.assertRaises(ValueError):self.transfer(True)
            self.policy['preimage_sha256']=route.sha(b'Z'*80000)
            self.preimage.write_bytes(b'X'*80000)
            with self.assertRaises(ValueError):self.transfer(True)

    def test_cid_mount_change_at_write_boundary(self):
        self.adapter.changed_at=2
        with mock.patch.object(route.os,'pwrite',side_effect=AssertionError('write attempted')):
            with self.assertRaises(ValueError):self.transfer(True)

    def test_preimage_race_refused(self):
        def mutate(fd,count):
            if count==2:os.pwrite(fd,b'X',route.START)
        self.adapter.mutate=mutate
        with self.assertRaises(ValueError):self.transfer(True)
        self.assertEqual(self.device.read_bytes()[route.START+1:route.START+80000],b'Z'*79999)

    def test_partition_overlap_refused(self):
        self.adapter.ranges=lambda fd:[(route.START,100)]
        with self.assertRaises(ValueError):self.transfer(True)

    def test_uncertain_partial_write_is_not_retried_or_rolled_back(self):
        real=os.pwrite
        def partial(fd,data,offset):return real(fd,data[:17],offset)
        with mock.patch.object(route.os,'pwrite',side_effect=partial) as call:
            with self.assertRaises(OSError):self.transfer(True)
            self.assertEqual(call.call_count,1)
        self.assertEqual(self.device.read_bytes()[route.START:route.START+18],b'L'*17+b'Z')

    def test_flush_failure_stops(self):
        with mock.patch.object(route.os,'fsync',side_effect=OSError('flush')):
            with self.assertRaises(OSError):self.transfer(True)
        self.assertEqual(self.device.read_bytes()[route.START:route.START+80000],b'L'*80000)

    def test_readback_corruption_stops_without_retry(self):
        def mutate(fd,count):
            if count==3:os.pwrite(fd,b'X',route.START)
        self.adapter.mutate=mutate
        with self.assertRaises(OSError):self.transfer(True)
        self.assertEqual(self.adapter.calls,3)

    def test_preservation_change_stops(self):
        def mutate(fd,count):
            if count==3:os.pwrite(fd,b'X',2*route.CHUNK)
        self.adapter.mutate=mutate
        with self.assertRaises(OSError):self.transfer(True)

    def test_cooperating_controller_exclusion(self):
        import fcntl
        fd=os.open(self.policy['ownership_lock'],os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.transfer()
        finally:os.close(fd)


class PreparationTests(unittest.TestCase):
    def test_only_three_commands_or_required_hash_dependency(self):
        old=b'# CONFIG_CMD_HASH is not set\n# CONFIG_HASH_VERIFY is not set\n# CONFIG_CRC32_VERIFY is not set\n'
        new=b'CONFIG_CMD_HASH=y\nCONFIG_HASH_VERIFY=y\nCONFIG_CRC32_VERIFY=y\n'
        self.assertEqual(len(route.config_delta(old,new)),3)
        self.assertEqual(len(route.config_delta(old,new+b'CONFIG_HASH=y\n')),4)
        with self.assertRaises(ValueError):route.config_delta(old,new+b'CONFIG_DRAM_CLK=720\n')
        with self.assertRaises(ValueError):route.config_delta(old,new.replace(b'CONFIG_HASH_VERIFY=y\n',b''))

    def test_invalid_fit_bounds(self):
        for data in (b'',b'X'*100):
            with self.assertRaises(ValueError):route.fit_properties(data)

    def test_supplied_actual_artifacts_prepare(self):
        p=Path(__file__).resolve().parents[1]/'local/managed-boot-inputs'
        if not (p/'new-provenance.json').exists():self.skipTest('Coordinator supplied build inputs absent')
        with tempfile.TemporaryDirectory() as work:
            out=Path(work)/'loader';receipt=Path(work)/'receipt.json'
            result=route.prepare(p/'old-loader.bin',p/'old.config',p/'new.config',p/'new.fit',
                p/'new.elf',p/'default.env',p/'old-provenance.json',p/'new-provenance.json',out,receipt)
            self.assertEqual(result['loader_sha256'],'350a941a7ec67b541308d235bffa4b937b8171f683f3e96b0c51dd32fab64544')
            self.assertEqual(out.read_bytes()[:route.SPL_BYTES],(p/'old-loader.bin').read_bytes()[:route.SPL_BYTES])
            self.assertFalse(result['physical_boot_validated'])
            with self.assertRaises(FileExistsError):
                route.prepare(p/'old-loader.bin',p/'old.config',p/'new.config',p/'new.fit',
                    p/'new.elf',p/'default.env',p/'old-provenance.json',p/'new-provenance.json',out,receipt)
            damaged=Path(work)/'bad.fit';data=bytearray((p/'new.fit').read_bytes())
            preserved=route.fit_properties(data)['/images/atf/data'];offset=data.index(preserved)
            data[offset]^=1;damaged.write_bytes(data)
            with self.assertRaises(ValueError):route.check_fit((p/'old.fit').read_bytes(),damaged.read_bytes())



class LinuxAdmissionTests(unittest.TestCase):
    """Execute production sysfs/mount checks against public disposable fixtures."""
    def setUp(self):
        from types import SimpleNamespace
        import stat
        import struct
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name);self.sys=self.work/'sys';self.proc=self.work/'proc'
        self.card=self.sys/'4020000.mmc'/'card';self.card.mkdir(parents=True)
        (self.card/'type').write_text('SD\n');(self.card/'cid').write_text('synthetic\n')
        self.block=self.sys/'block';self.block.mkdir();(self.block/'device').symlink_to(self.card)
        (self.block/'dev').write_text('179:16\n');(self.block/'holders').mkdir()
        for n in (1,2):
            child=self.block/f'p{n}';child.mkdir();(child/'partition').write_text(str(n))
            (child/'dev').write_text(f'179:{16+n}');(child/'holders').mkdir()
        (self.sys/'179:16').symlink_to(self.block)
        (self.proc/'self').mkdir(parents=True)
        self.mount=self.proc/'self/mountinfo'
        self.mount.write_text('21 1 179:18 / / ro - ext4 /dev/mmcblk2p2 ro,norecovery\n')
        self.device=self.work/'device';self.device.write_bytes(b'fixture');self.fd=os.open(self.device,os.O_RDONLY)
        self.addCleanup(os.close,self.fd)
        self.policy={'dev_t':'179:16','root_dev_t':'179:18','boot_dev_t':'179:17',
            'cid':'synthetic','controller':'4020000.mmc','capacity':4096,
            'image_bytes':4096,'disk_guid':'fixture-guid','partitions':[]}
        real_path=Path
        def paths(value):
            return {'/sys/dev/block':self.sys,'/proc':self.proc,
                    '/proc/self/mountinfo':self.mount}.get(str(value),real_path(value))
        real_open=os.open
        def opens(path,*args):
            if str(path)=='/dev/block/179:18':return real_open(self.device,*args)
            return real_open(path,*args)
        def fstats(fd):
            return SimpleNamespace(st_mode=stat.S_IFBLK,st_rdev=os.makedev(179,16 if fd==self.fd else 18))
        def ioctl(fd,op,*args):
            return struct.pack('Q',4096) if op==0x80081272 else struct.pack('I',1)
        for patcher in (mock.patch.object(route,'Path',side_effect=paths),
                        mock.patch.object(route.os,'open',side_effect=opens),
                        mock.patch.object(route.os,'fstat',side_effect=fstats),
                        mock.patch.object(route.fcntl,'ioctl',side_effect=ioctl),
                        mock.patch.object(route,'inspect_gpt',return_value={'disk_guid':'fixture-guid','partition_records':[]})):
            patcher.start();self.addCleanup(patcher.stop)
        self.adapter=route.LinuxSD(self.policy)

    def test_actual_admission_pass(self):
        result=self.adapter.admission(self.fd)
        self.assertEqual(result['controller'],'4020000.mmc')

    def test_sysfs_cid_controller_card_type_capacity_refusal(self):
        for key,value in (('cid','changed'),('controller','other'),('capacity',8192),('dev_t','179:99')):
            with self.subTest(key=key):
                bad=route.LinuxSD({**self.policy,key:value})
                with self.assertRaises(ValueError):bad.admission(self.fd)
        (self.card/'type').write_text('MMC')
        with self.assertRaises(ValueError):self.adapter.admission(self.fd)

    def test_writable_root_missing_norecovery_and_mounted_boot_refused(self):
        variants=('21 1 179:18 / / rw - ext4 /dev/mmcblk2p2 rw,norecovery\n',
                  '21 1 179:18 / / ro - ext4 /dev/mmcblk2p2 ro\n',
                  self.mount.read_text()+'22 1 179:17 / /boot ro - vfat /dev/mmcblk2p1 ro\n')
        for text in variants:
            self.mount.write_text(text)
            with self.assertRaises(ValueError):self.adapter.admission(self.fd)

    def test_kernel_readonly_and_holders_required(self):
        import struct
        real=route.fcntl.ioctl
        def ioctl(fd,op,*args):return struct.pack('I',0) if op==0x125e else real(fd,op,*args)
        with mock.patch.object(route.fcntl,'ioctl',side_effect=ioctl):
            with self.assertRaises(ValueError):self.adapter.admission(self.fd)
        (self.block/'p1/holders/other').touch()
        with self.assertRaises(ValueError):self.adapter.admission(self.fd)

    def test_other_namespace_writable_sd_mount_refused(self):
        process=self.proc/'12345';process.mkdir();(process/'fd').mkdir()
        (process/'mountinfo').write_text('2 1 179:17 / /other rw - vfat fixture rw\n')
        with self.assertRaises(ValueError):self.adapter.admission(self.fd)

    def test_reviewed_gpt_mismatch_refused(self):
        with mock.patch.object(route,'inspect_gpt',return_value={'disk_guid':'changed','partition_records':[]}):
            with self.assertRaises(ValueError):self.adapter.admission(self.fd)


if __name__=='__main__':unittest.main()
