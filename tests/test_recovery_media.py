import copy
from contextlib import contextmanager
import errno
import json
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_recovery_media import (Kernel, MediaProvider, PROTOCOL, WRITER_MODEL,
                                 POLICY, Unavailable, admitted_system_mount, durable_identity, fingerprint, mount_table,
                                 canonical_json, opened, production_adapter, same_identity, strict_envelope_manifest,
                                 reviewed_inventory, trusted_file)
from sv08_recovery import RecoveryController, installed_controller
from sv08_state import Store


class SysfsInventoryTests(unittest.TestCase):
    """Real discovery over disposable sysfs files, never host block devices."""
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.sysfs=self.root/'sys';self.dev=self.root/'dev';self.dev.mkdir()
        (self.sysfs/'class/block').mkdir(parents=True);(self.sysfs/'dev/block').mkdir(parents=True)
        self.card=self.sysfs/'devices/platform/mmc_host/mmc3/mmc3:001a'
        self.disk=self.card/'block/mmcblk3'
        self.numbers={}
        self.node(self.disk,'179:32',234567,3,ro='0')
        (self.card/'type').write_text('MMC\n');(self.card/'cid').write_text('synthetic-cid\n')
        (self.disk/'device').symlink_to(self.card)
        self.partition=self.disk/'mmcblk3p1'
        self.node(self.partition,'179:33',123456,0,ro='0')
        (self.partition/'partition').write_text('1\n');(self.partition/'start').write_text('2048\n')
        self.areas=[]
        for index,device in enumerate(('179:40','179:48')):
            area=self.disk/('mmcblk3boot'+str(index));self.areas.append(area)
            self.node(area,device,8192,10+index)
            (area/'force_ro').write_text('1\n')

    def node(self,path,device,sectors,sequence,ro='1'):
        path.mkdir(parents=True)
        for key,value in dict(dev=device,size=sectors,diskseq=sequence,ro=ro,removable=0,
                              uevent='DEVNAME='+path.name).items():
            (path/key).write_text(str(value)+'\n')
        for key in ('holders','slaves'):(path/key).mkdir()
        (self.sysfs/'class/block'/path.name).symlink_to(path)
        (self.sysfs/'dev/block'/device).symlink_to(path)
        (self.dev/path.name).write_text('synthetic filesystem signature')
        self.numbers[path.name]=device

    @contextmanager
    def discovered(self):
        original_stat=os.stat
        def fake_block(path,*args,**kwargs):
            path=Path(path)
            if path.parent==self.dev and path.name in self.numbers:
                major,minor=map(int,self.numbers[path.name].split(':'))
                return SimpleNamespace(st_mode=stat.S_IFBLK|0o600,st_rdev=os.makedev(major,minor))
            return original_stat(path,*args,**kwargs)
        def probe(path):
            self.assertNotIn('boot',path.name,'Boot area reached blkid despite a fake FS signature')
            return dict(TYPE='ext4',UUID='fixture-partition') if path==self.dev/self.partition.name else {}
        with patch.object(Kernel,'sysfs_root',self.sysfs),patch.object(Kernel,'device_root',self.dev), \
             patch('sv08_recovery_media.os.stat',fake_block),patch.object(Kernel,'_probe',side_effect=probe):
            yield Kernel()

    def test_discovers_owned_protected_areas_without_independent_stable_id_or_probe(self):
        with self.discovered() as kernel:
            observed=kernel.inventory()
            (self.disk/'ro').write_text('1\n')
            protected_after_user_area_ro=kernel.inventory()[0]['boot_areas']
            (self.areas[0]/'diskseq').write_text('12\n')
            resequenced=kernel.inventory()
            (self.areas[0]/'size').write_text('8193\n')
            resized=kernel.inventory()
        self.assertEqual(len(observed),1);disk=observed[0]
        self.assertEqual(disk['stable'],{'device/cid':'synthetic-cid'})
        self.assertEqual(len(disk['partitions']),1)
        self.assertEqual([area['device'] for area in disk['boot_areas']],['179:40','179:48'])
        self.assertEqual([area['diskseq'] for area in disk['boot_areas']],[10,11])
        self.assertTrue(all(area['readonly'] and area['force_readonly'] and not area['removable']
                            and area['disk_device']=='179:32' and 'stable' not in area
                            for area in disk['boot_areas']))
        self.assertEqual(protected_after_user_area_ro,disk['boot_areas'])
        reviewed=reviewed_inventory(observed)
        self.assertEqual(reviewed[0]['boot_areas'],[dict(index=0,sectors=8192),dict(index=1,sectors=8192)])
        self.assertEqual(resequenced[0]['boot_areas'][0]['diskseq'],12)
        self.assertNotEqual(resequenced,observed);self.assertEqual(reviewed_inventory(resequenced),reviewed)
        self.assertEqual(resized[0]['boot_areas'][0]['sectors'],8193)
        self.assertNotEqual(reviewed_inventory(resized),reviewed)
        for field in ('sectors','index'):
            changed=copy.deepcopy(observed);changed[0]['boot_areas'][0][field]+=1
            self.assertNotEqual(reviewed_inventory(changed),reviewed)
        changed=copy.deepcopy(observed);changed[0]['boot_areas'].pop()
        self.assertNotEqual(reviewed_inventory(changed),reviewed)

    def test_boot_area_cannot_be_selected_even_with_filesystem_signature(self):
        from sv08_recovery_prepare import PreparationKernel
        with self.discovered() as kernel,patch('sv08_recovery_media.subprocess.run') as command:
            for area in self.areas:
                with self.assertRaisesRegex(ValueError,'cannot be selected'):
                    kernel.block(dict(device=(area/'dev').read_text().strip(),filesystem='ext4'))
                with self.assertRaisesRegex(ValueError,'cannot be selected'):kernel._identity(area)
                with patch('sv08_recovery_prepare.os.open',side_effect=AssertionError('Auxiliary opened')):
                    for whole in (False,True):
                        with self.assertRaisesRegex(ValueError,'cannot be selected'):
                            PreparationKernel._open_identity(dict(sysfs=str(area)),whole=whole)
            command.assert_not_called()

    def test_missing_wrong_type_parent_ancestry_and_name_fail_closed(self):
        with self.discovered() as kernel:
            (self.card/'type').write_text('SD\n')
            with self.assertRaisesRegex(ValueError,'ownership or type'):kernel.inventory()
            (self.card/'type').unlink()
            with self.assertRaises(OSError):kernel.inventory()
            (self.card/'type').write_text('MMC\n')
            parent_link=self.sysfs/'class/block/mmcblk3';parent_link.unlink()
            with self.assertRaisesRegex(ValueError,'owning medium'):kernel.inventory()
            parent_link.symlink_to(self.disk)
            device_link=self.disk/'device';device_link.unlink();device_link.mkdir()
            (device_link/'type').write_text('MMC\n')
            with self.assertRaisesRegex(ValueError,'ownership or type'):kernel.inventory()
            (device_link/'type').unlink();device_link.rmdir();device_link.symlink_to(self.card)
            area=self.areas[0];wrong=self.card/area.name;area.rename(wrong)
            link=self.sysfs/'class/block'/area.name;link.unlink();link.symlink_to(wrong)
            with self.assertRaisesRegex(ValueError,'owning medium'):kernel.inventory()
            wrong.rename(area);link.unlink();link.symlink_to(area)
            malformed=self.disk/'mmcblk3boot2';self.node(malformed,'179:56',8192,12)
            with self.assertRaisesRegex(ValueError,'cannot be selected'):kernel.inventory()

    def test_missing_changed_properties_and_topology_fail_closed(self):
        with self.discovered() as kernel:
            for key,value in (('ro','0'),('force_ro','0'),('removable','1'),('size','0'),('diskseq','0'),
                              ('uevent','DEVNAME=mmcblk99boot0'),('partition','1')):
                path=self.areas[0]/key;old=path.read_bytes() if path.exists() else None
                path.write_text(value+'\n')
                with self.subTest(key=key),self.assertRaises(ValueError):kernel.inventory()
                if old is None:path.unlink()
                else:path.write_bytes(old)
            for key in ('force_ro','removable','diskseq','size'):
                path=self.areas[0]/key;old=path.read_bytes();path.unlink()
                with self.subTest(missing=key),self.assertRaises(OSError):kernel.inventory()
                path.write_bytes(old)
            for key in ('holders','slaves'):
                path=self.areas[0]/key/'unexpected';path.touch()
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'holder or slave'):kernel.inventory()
                path.unlink()
            (self.sysfs/'class/block'/self.areas[1].name).unlink()
            with self.assertRaisesRegex(ValueError,'Incomplete'):kernel.inventory()

    def test_generic_non_mmc_inventory_keeps_legacy_shape(self):
        import shutil
        shutil.rmtree(self.sysfs);(self.sysfs/'class/block').mkdir(parents=True)
        (self.sysfs/'dev/block').mkdir(parents=True)
        disk=self.sysfs/'devices/pci/virtio0/block/vda';self.node(disk,'254:7',4096,21)
        (disk/'serial').write_text('synthetic-virtio\n')
        with self.discovered() as kernel:observed=kernel.inventory()
        self.assertEqual(len(observed),1);self.assertNotIn('boot_areas',observed[0])
        self.assertEqual(observed[0]['transport'],'virtio')

    def test_provider_census_rejects_auxiliary_mount_before_selected_mounts(self):
        provider=MediaProvider.__new__(MediaProvider);provider.kernel=Kernel()
        observed=dict(media=[dict(boot_areas=[dict(device='179:48')])])
        with patch.object(provider,'complete_inventory',return_value={**observed,'active_loops':[{}]}), \
             patch.object(provider.kernel,'mounts',return_value=[dict(device='179:48',path='/fake')]):
            with self.assertRaisesRegex(ValueError,'boot area has an unexpected mount'):provider.snapshot()


class UsbIdentityTests(unittest.TestCase):
    """Descriptor identity is bound to real USB ownership in disposable sysfs."""
    node = SysfsInventoryTests.node
    discovered = SysfsInventoryTests.discovered

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.sysfs, self.dev = self.root/'sys', self.root/'dev'
        self.dev.mkdir()
        for name in ('class/block', 'dev/block', 'bus/usb/drivers/usb-storage',
                     'bus/usb/drivers/uas'):
            (self.sysfs/name).mkdir(parents=True)
        self.hub = self.sysfs/'devices/pci/usb1'
        self.owner = self.hub/'1-2'
        self.interface = self.owner/'1-2:1.0'
        self.scsi = self.interface/'host4/target4:0:0/4:0:0:0'
        self.disk = self.scsi/'block/sda'
        self.numbers = {}
        self.node(self.disk, '8:0', 40000, 32)
        (self.disk/'device').symlink_to(self.scsi)
        self.partition = self.disk/'sda1'
        self.node(self.partition, '8:1', 30000, 0)
        (self.partition/'partition').write_text('1\n')
        (self.partition/'start').write_text('2048\n')
        for node, kind in ((self.hub, 'usb_device'), (self.owner, 'usb_device'),
                           (self.interface, 'usb_interface')):
            (node/'subsystem').symlink_to(self.sysfs/'bus/usb')
            (node/'uevent').write_text('DEVTYPE='+kind+'\n')
        (self.interface/'driver').symlink_to(self.sysfs/'bus/usb/drivers/usb-storage')
        (self.interface/'bInterfaceClass').write_text('08\n')
        (self.owner/'idVendor').write_text('AB12\n')
        (self.owner/'idProduct').write_text('0034\n')
        (self.owner/'serial').write_text('media-serial\n')
        (self.hub/'serial').write_text('controller-serial\n')
        self.expected = {'usb/serial': 'media-serial',
                         'usb/device': ['ab12', '0034', 'media-serial']}

    def observations(self, kernel):
        # block() probes its selected mounted node; inventory probes all nodes.
        with patch('sv08_recovery_media.subprocess.run', return_value=SimpleNamespace(
                stdout='TYPE=ext4\nUUID=fixture-partition\n')):
            return kernel.block(dict(device='8:1', filesystem='ext4')), kernel.inventory()

    def test_both_entry_points_fallback_and_changed_descriptor_inventory(self):
        with self.discovered() as kernel:
            block, inventory = self.observations(kernel)
            self.assertEqual(block['stable'], self.expected)
            self.assertEqual(inventory[0]['stable'], self.expected)
            self.assertEqual(inventory[0]['transport'], 'usb-scsi')
            old = reviewed_inventory(inventory)
            (self.owner/'serial').write_text('replacement\n')
            changed, inventory = self.observations(kernel)
            self.assertNotEqual(changed['stable'], block['stable'])
            self.assertNotEqual(durable_identity(changed), durable_identity(block))
            self.assertNotEqual(reviewed_inventory(inventory), old)

    def test_legacy_values_preserved_and_each_attribute_read_once(self):
        values = {'wwid': 'disk-wwid', 'device/wwid': 'scsi-wwid',
                  'device/cid': 'cid', 'device/serial': 'scsi-serial', 'serial': 'disk-serial'}
        for name, value in values.items():
            (self.disk/name).write_text(value+'\n')
        original = Path.read_text
        for entry in ('block', 'inventory'):
            reads = []
            def read(path, *args, **kwargs):
                reads.append(path)
                return original(path, *args, **kwargs)
            with self.discovered() as kernel, patch.object(Path, 'read_text', read), \
                 patch('sv08_recovery_media.subprocess.run', return_value=SimpleNamespace(
                     stdout='TYPE=ext4\nUUID=fixture-partition\n')):
                observed = (kernel.block(dict(device='8:1', filesystem='ext4')) if entry == 'block'
                            else kernel.inventory()[0])
            self.assertEqual(observed['stable'], values)
            for name in values:
                self.assertEqual(reads.count(self.disk/name), 1, (entry, name))
            self.assertNotIn(self.owner/'serial', reads)

    def test_optional_wwid_errors_require_an_independent_identity(self):
        (self.scsi/'wwid').write_text('unreadable')
        original = Path.read_text
        for code in (errno.ENXIO, errno.EINVAL, errno.EIO, errno.EACCES, errno.ENODEV, errno.ENOENT):
            def read(path, *args, **kwargs):
                if path == self.disk/'device/wwid':
                    raise OSError(code, 'injected optional WWID read failure')
                return original(path, *args, **kwargs)
            with self.subTest(errno=code), self.discovered() as kernel, patch.object(Path, 'read_text', read):
                if code in (errno.ENXIO, errno.EINVAL):
                    block, inventory = self.observations(kernel)
                    self.assertEqual(block['stable'], self.expected)
                    self.assertEqual(inventory[0]['stable'], self.expected)
                else:
                    for call in (lambda: self.observations(kernel), kernel.inventory):
                        with self.assertRaises(OSError): call()
        # Unsupported WWID errors can also coexist with a usable legacy serial.
        (self.disk/'serial').write_text('legacy\n')
        def unsupported(path, *args, **kwargs):
            if path == self.disk/'device/wwid': raise OSError(errno.ENXIO, 'unsupported')
            return original(path, *args, **kwargs)
        with self.discovered() as kernel, patch.object(Path, 'read_text', unsupported):
            block, inventory = self.observations(kernel)
            self.assertEqual(block['stable'], {'serial': 'legacy'})
            self.assertEqual(inventory[0]['stable'], {'serial': 'legacy'})
        (self.disk/'serial').unlink()
        (self.owner/'serial').write_text('\n')
        with self.discovered() as kernel, patch.object(Path, 'read_text', unsupported):
            with self.assertRaises(ValueError): self.observations(kernel)
            with self.assertRaises(ValueError): kernel.inventory()

    def test_nearest_descriptor_never_borrows_hub_and_io_fails_closed(self):
        for name, value in (('serial', ''), ('serial', 'bad\x01serial'),
                            ('idVendor', '123'), ('idProduct', 'zzzz')):
            path = self.owner/name
            old = path.read_bytes()
            path.write_text(value+'\n')
            with self.subTest(name=name, value=value), self.discovered() as kernel:
                with self.assertRaises(ValueError): self.observations(kernel)
                with self.assertRaises(ValueError): kernel.inventory()
            path.write_bytes(old)
        for name in ('serial', 'idVendor', 'idProduct'):
            path = self.owner/name
            old = path.read_bytes()
            path.unlink()
            with self.subTest(missing=name), self.discovered() as kernel:
                with self.assertRaises(OSError): self.observations(kernel)
                with self.assertRaises(OSError): kernel.inventory()
            path.write_bytes(old)
        original = Path.read_text
        for code in (errno.ENXIO, errno.EINVAL, errno.EACCES, errno.EIO, errno.ENODEV):
            def read(path, *args, **kwargs):
                if path == self.owner/'serial': raise OSError(code, 'descriptor unavailable')
                return original(path, *args, **kwargs)
            with self.subTest(errno=code), self.discovered() as kernel, patch.object(Path, 'read_text', read):
                with self.assertRaises(OSError): self.observations(kernel)
                with self.assertRaises(OSError): kernel.inventory()

    def test_wrong_usb_ancestry_interface_and_root_hub_refuse(self):
        for path, value in ((self.interface/'bInterfaceClass', '09'),
                            (self.interface/'uevent', 'DEVTYPE=usb_device'),
                            (self.owner/'uevent', 'DEVTYPE=usb_interface')):
            old = path.read_bytes()
            path.write_text(value+'\n')
            with self.subTest(path=path), self.discovered() as kernel:
                with self.assertRaises(ValueError): self.observations(kernel)
                with self.assertRaises(ValueError): kernel.inventory()
            path.write_bytes(old)
        for path, target in ((self.interface/'driver', self.sysfs/'bus/usb/drivers'),
                             (self.owner/'subsystem', self.sysfs/'bus')):
            old = path.readlink()
            path.unlink(); path.symlink_to(target)
            with self.discovered() as kernel:
                with self.assertRaises(ValueError): self.observations(kernel)
                with self.assertRaises(ValueError): kernel.inventory()
            path.unlink(); path.symlink_to(old)
        # Missing the actual device/interface metadata exposes the hub as the
        # nearest USB ancestor; its own valid serial must not become identity.
        for node in (self.interface, self.owner): (node/'subsystem').unlink()
        with self.discovered() as kernel:
            with self.assertRaises(ValueError): self.observations(kernel)
            with self.assertRaises(ValueError): kernel.inventory()

    def test_multi_lun_refuses_even_with_distinct_wwids(self):
        (self.disk/'wwid').write_text('first-lun\n')
        second = self.interface/'host4/target4:0:0/4:0:0:1/block/sdb'
        self.node(second, '8:16', 40000, 33)
        (second/'wwid').write_text('second-lun\n')
        with self.discovered() as kernel:
            with self.assertRaisesRegex(ValueError, 'LUN'): self.observations(kernel)
            with self.assertRaisesRegex(ValueError, 'LUN'): kernel.inventory()

    def test_uas_and_cross_interface_lun_ownership(self):
        driver = self.interface/'driver'
        driver.unlink(); driver.symlink_to(self.sysfs/'bus/usb/drivers/uas')
        with self.discovered() as kernel:
            block, inventory = self.observations(kernel)
            self.assertEqual(block['stable'], inventory[0]['stable'])
        second = self.owner/'1-2:1.1/host5/target5:0:0/5:0:0:0/block/sdb'
        self.node(second, '8:16', 40000, 33)
        (self.disk/'wwid').write_text('first-interface\n')
        (second/'wwid').write_text('second-interface\n')
        with self.discovered() as kernel:
            with self.assertRaisesRegex(ValueError, 'LUN'): self.observations(kernel)
            with self.assertRaisesRegex(ValueError, 'LUN'): kernel.inventory()

    def test_unsupported_wwid_without_any_identity_refuses(self):
        # A non-USB disk has no descriptor fallback; unsupported WWID alone
        # remains a refusal rather than an invented filesystem/device identity.
        import shutil
        shutil.rmtree(self.sysfs/'devices')
        for directory in ('class/block', 'dev/block'):
            for link in (self.sysfs/directory).iterdir(): link.unlink()
        self.disk = self.sysfs/'devices/pci/virtio0/block/vda'
        self.node(self.disk, '254:0', 40000, 34)
        (self.disk/'wwid').write_text('unreadable')
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path == self.disk/'wwid': raise OSError(errno.EINVAL, 'unsupported')
            return original(path, *args, **kwargs)
        with self.discovered() as kernel, patch.object(Path, 'read_text', read):
            with self.assertRaises(OSError): kernel.inventory()
            with self.assertRaises(OSError): kernel.block(dict(device='254:0', filesystem='ext4'))

    def test_serial_aliases_keep_all_conflicting_values(self):
        for legacy in ({'serial': 'other', 'device/serial': 'media-serial'},
                       {'device/serial': 'other', 'serial': 'media-serial'}):
            for left, right in ((self.expected, legacy), (legacy, self.expected)):
                self.assertTrue(same_identity(left, right))
        self.assertFalse(same_identity(self.expected, {'serial': 'other'}))
        self.assertFalse(same_identity(self.expected,
            {'usb/device': ['ab12', '0034', 'other'], 'usb/serial': 'other'}))
        self.assertFalse(same_identity(self.expected, {'idVendor': 'ab12', 'idProduct': '0034'}))


class RecoveryMediaTests(unittest.TestCase):
    def setUp(self):
        self.policy = dict(format_version=1, kind='independent-recovery', protocol=PROTOCOL,
                           writer_model=WRITER_MODEL, image_manifest_sha256='1'*64,
                           recovery={}, source={}, system_media=[{'wwid':'reviewed-root'}])
        self.context = dict(format_version=1, protocol=PROTOCOL, policy_sha256=fingerprint(self.policy),
                            source='/data', destinations={'usb': dict(path='/media/usb', label='Reviewed USB')},
                            expected={})

    def adapter(self, policy, context):
        with patch('sv08_recovery_media.trusted_file', side_effect=[canonical_json(policy), json.dumps(context).encode()]):
            return production_adapter()

    def test_mount_parser_distinguishes_vfs_from_superblock_and_decodes_paths(self):
        mounts = mount_table('41 30 8:1 / /source\\040data ro,noatime - ext4 /dev/sda1 rw,norecovery\n')
        self.assertEqual(mounts[0]['path'], '/source data')
        self.assertIn('ro', mounts[0]['options'])
        self.assertIn('rw', mounts[0]['super_options'])
        self.assertNotIn('ro', mounts[0]['super_options'])

    def test_only_exact_selected_kernel_api_mounts_are_admitted(self):
        text = '''
34 27 0:7 / /sys/kernel/security rw,nosuid,nodev,noexec,relatime - securityfs securityfs rw
37 27 0:31 / /sys/fs/pstore rw,nosuid,nodev,noexec,relatime - pstore pstore rw
38 27 0:32 / /sys/fs/bpf rw,nosuid,nodev,noexec,relatime - bpf bpf rw,mode=700
39 28 0:23 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
41 27 0:13 / /sys/kernel/tracing rw,nosuid,nodev,noexec,relatime - tracefs tracefs rw
42 27 0:8 / /sys/kernel/debug rw,nosuid,nodev,noexec,relatime - debugfs debugfs rw
40 28 0:35 / /dev/hugepages rw,nosuid,nodev,relatime - hugetlbfs hugetlbfs rw,pagesize=2M
45 27 0:37 / /sys/fs/fuse/connections rw,nosuid,nodev,noexec,relatime - fusectl fusectl rw
46 27 0:38 / /sys/kernel/config rw,nosuid,nodev,noexec,relatime - configfs configfs rw
'''.strip()
        mounts = mount_table(text)
        self.assertTrue(all(admitted_system_mount(mount, set()) for mount in mounts))
        for mount in mounts:
            mutations = {
                'path': '/sys/kernel/not-reviewed', 'root': '/subtree',
                'filesystem': 'sysfs', 'source': 'unreviewed',
                'options': mount['options'][1:], 'super_options': ['ro'],
            }
            for field, value in mutations.items():
                changed = {**mount, field:value}
                with self.subTest(path=mount['path'], field=field):
                    self.assertFalse(admitted_system_mount(changed, set()))

    def test_ambiguous_mounts_and_nonblock_topology_refused(self):
        line = '41 30 8:1 / /data ro - ext4 /dev/sda1 ro\n'
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            mount_table(line+line.replace('41 ', '42 ', 1))
        with self.assertRaisesRegex(ValueError, 'non-block'):
            Kernel().block({'device':'0:35'})

    @staticmethod
    def proc_fixture(root, namespace='mnt:[1]', pid_namespace='pid:[1]'):
        task=root/'101/task/101';(task/'ns').mkdir(parents=True)
        (task/'stat').write_text('101 (fixture) S 1 1 1 0 -1 0\n')
        (task/'ns/mnt').symlink_to(namespace)
        (task/'ns/pid').symlink_to(pid_namespace)
        return root/'101',task

    def test_namespace_census_skips_only_pinned_disappearing_entries(self):
        original_open=os.open
        for stage, error in (('process', FileNotFoundError()),
                             ('thread', ProcessLookupError()),
                             ('stat', FileNotFoundError())):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                proc=Path(directory);self.proc_fixture(proc);numeric_opens=0
                def opening(path, flags, mode=0o777, *, dir_fd=None):
                    nonlocal numeric_opens
                    if str(path) == '101':
                        numeric_opens += 1
                        if ((stage == 'process' and numeric_opens == 1) or
                                (stage == 'thread' and numeric_opens == 2)):
                            raise error
                    if stage == 'stat' and path == 'stat':
                        raise error
                    return original_open(path, flags, mode, dir_fd=dir_fd)
                with patch('sv08_recovery_media.os.open', side_effect=opening):
                    Kernel()._namespace_census('mnt:[1]', 'pid:[1]', proc)

    def test_pinned_process_cannot_redirect_to_reused_pid_path(self):
        original_open=os.open
        with tempfile.TemporaryDirectory() as directory:
            proc=Path(directory);process,_=self.proc_fixture(proc);replaced=False
            def opening(path, flags, mode=0o777, *, dir_fd=None):
                nonlocal replaced
                fd=original_open(path, flags, mode, dir_fd=dir_fd)
                if path == '101' and not replaced:
                    replaced=True
                    process.rename(proc/'old')
                    self.proc_fixture(proc, namespace='mnt:[different]')
                return fd
            with patch('sv08_recovery_media.os.open', side_effect=opening):
                Kernel()._namespace_census('mnt:[1]', 'pid:[1]', proc)
            with self.assertRaisesRegex(ValueError, 'Unexpected process namespace'):
                Kernel()._namespace_census('mnt:[1]', 'pid:[1]', proc)

    def test_namespace_census_refuses_live_errors_malformed_stat_and_mismatch(self):
        original_open=os.open
        for failure in ('permission', 'io', 'missing-namespace', 'malformed', 'mismatch'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                proc=Path(directory);_,task=self.proc_fixture(proc)
                if failure == 'missing-namespace':(task/'ns/mnt').unlink()
                elif failure == 'malformed':(task/'stat').write_text('malformed\n')
                elif failure == 'mismatch':
                    (task/'ns/mnt').unlink();(task/'ns/mnt').symlink_to('mnt:[different]')
                def opening(path, flags, mode=0o777, *, dir_fd=None):
                    if path == 'stat' and failure == 'permission':raise PermissionError(errno.EACCES, 'denied')
                    if path == 'stat' and failure == 'io':raise OSError(errno.EIO, 'io')
                    return original_open(path, flags, mode, dir_fd=dir_fd)
                expected = ValueError if failure in ('malformed', 'mismatch') else OSError
                with patch('sv08_recovery_media.os.open', side_effect=opening), \
                     self.assertRaises(expected):
                    Kernel()._namespace_census('mnt:[1]', 'pid:[1]', proc)

    def test_identity_matching_supports_disposable_file_identity_lists(self):
        self.assertTrue(same_identity({'identity':[7, 11, 1024]}, {'identity':[7, 11, 1024]}))
        self.assertFalse(same_identity({'identity':[7, 11, 1024]}, {'identity':[7, 12, 1024]}))

    def test_envelope_manifest_parser_is_fixed_and_unambiguous(self):
        data = (b'format=sv08-recovery-usr-v1\nroot_uuid=root\nroot_bytes=536870912\n'
                b'usr_path=/usr.squashfs\nusr_bytes=513\nusr_sha256=' + b'a'*64 + b'\n')
        value = strict_envelope_manifest(data)
        self.assertEqual(value['usr_bytes'], 513)
        for damaged in (data+b'extra=x\n', data.replace(b'usr_path=', b'path='), data.rstrip(b'\n')):
            with self.assertRaisesRegex(ValueError, 'manifest'): strict_envelope_manifest(damaged)

    def test_compressed_chain_binds_file_loop_extent_and_squashfs_mount(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); backing = root/'usr.squashfs'; backing.write_bytes(b'x'*513)
            digest = hashlib.sha256(backing.read_bytes()).hexdigest()
            actual = backing.stat(); provider = MediaProvider.__new__(MediaProvider); provider.root = root
            mount = dict(path='/usr', root='/', filesystem='squashfs', options=['ro'],
                         super_options=['ro'], device='7:0')
            recovery = dict(directory=[actual.st_dev, root.stat().st_ino])
            envelope = dict(usr_path='/usr.squashfs', usr_bytes=513, usr_sha256=digest)
            node = Path('/sys/devices/virtual/block/loop0')
            values = {str(node/'ro'):'1', str(node/'loop/offset'):'0',
                      str(node/'loop/sizelimit'):'0', str(node/'size'):'2',
                      str(node/'loop/backing_file'):'/usr.squashfs'}
            original_fstat, original_stat = os.fstat, os.stat
            def owned(fd):
                value=list(original_fstat(fd));value[4]=value[5]=0
                return os.stat_result(value)
            def stat_path(path, *args, **kwargs):
                if str(path) == '/usr.squashfs':
                    value=list(original_stat(backing));value[4]=value[5]=0
                    return os.stat_result(value)
                return original_stat(path, *args, **kwargs)
            def read(path, *args, **kwargs): return values[str(path)]
            with patch('sv08_recovery_media.os.fstat', owned), \
                 patch('sv08_recovery_media.os.stat', stat_path), \
                 patch('sv08_recovery_media.Path.resolve', return_value=node), \
                 patch('sv08_recovery_media.Path.read_text', read), \
                 patch('sv08_recovery_media.Path.iterdir', return_value=[]), \
                 patch('sv08_recovery_media.Path.is_dir', return_value=True), \
                 patch('sv08_recovery_media.Path.stat', return_value=SimpleNamespace(st_ino=88)):
                result = provider.compressed_userspace([mount], recovery, envelope)
                self.assertEqual(result['backing'][2], 513)
                values[str(node/'loop/offset')] = '1'
                with self.assertRaisesRegex(ValueError, 'offset'):
                    provider.compressed_userspace([mount], recovery, envelope)
                values[str(node/'loop/offset')] = '0'; values[str(node/'loop/sizelimit')] = '1024'
                with self.assertRaisesRegex(ValueError, 'extent'):
                    provider.compressed_userspace([mount], recovery, envelope)

    def test_absent_and_malformed_production_contexts_are_diagnostic_only(self):
        with patch('sv08_recovery_media.trusted_file', side_effect=FileNotFoundError('Recovery context is absent')):
            adapter = production_adapter()
            self.assertIsInstance(adapter, Unavailable)
            self.assertIn('absent', adapter.reason)
        with patch('sv08_recovery_media.trusted_file', return_value=b'{broken'):
            self.assertIsInstance(production_adapter(), Unavailable)
        cases = [(None, self.context), ([], self.context), (self.policy, None), (self.policy, [])]
        for field, values in {'format_version':[True, '1'], 'destinations':[[], 'usb', None, {'usb':None}, {'usb':dict(path=None,label='USB')}],
                              'source':[None, '/data/../data', 'data']}.items():
            for value in values:
                context = copy.deepcopy(self.context);context[field] = value
                cases.append((self.policy, context))
        for policy, context in cases:
            with self.subTest(policy=policy, context=context):
                with patch('sv08_recovery_media.MediaLease', side_effect=AssertionError('Malformed configuration reached admission')):
                    adapter = self.adapter(policy, context)
                self.assertIsInstance(adapter, Unavailable)
                self.assertFalse(adapter.capability('recovery.export', {})[0])
                self.assertEqual(adapter.destinations(), [])

    def test_fixture_policy_cannot_enable_production(self):
        policy = {**self.policy, 'kind':'disposable-recovery-fixture'}
        context = {**self.context, 'policy_sha256':fingerprint(policy)}
        adapter = self.adapter(policy, context)
        self.assertIsInstance(adapter, Unavailable)
        self.assertIn('independent recovery', adapter.reason)

    def test_v2_policy_derives_protected_system_media_without_trusting_context(self):
        recovery = {'serial':'recovery'}; source = {'device/wwid':'source'}; usb = {'device/wwid':'usb'}
        policy = {key:value for key,value in self.policy.items()
                  if key not in ('image_manifest_sha256', 'system_media')}
        policy.update(format_version=2, envelope_manifest_sha256='2'*64,
                      source_path='/data',
                      recovery={'stable':recovery}, source={'stable':source},
                      media=[dict(stable=recovery), dict(stable=source), dict(stable=usb)],
                      protected=[], destinations={'usb':dict(identity=dict(stable=usb),
                                      path='/media/usb', label='Reviewed USB')})
        context = {**self.context, 'format_version':2, 'policy_sha256':fingerprint(policy)}
        provider = MediaProvider(policy, context)
        self.assertEqual(provider.system_media, [recovery, source])
        changed = copy.deepcopy(context); changed['source'] = '/other'
        with self.assertRaisesRegex(ValueError, 'immutable source'):
            MediaProvider(policy, changed)
        aliased = copy.deepcopy(policy)
        aliased['protected'] = [dict(role='slot-a', identity=dict(stable=usb))]
        aliased_context = {**context, 'policy_sha256':fingerprint(aliased)}
        with self.assertRaisesRegex(ValueError, 'whole disk aliases protected'):
            MediaProvider(aliased, aliased_context)

    def test_v2_complete_inventory_rechecks_unmounted_media_and_active_loops(self):
        def disk(index, stable, uuid, removable=False):
            device=f'{index}:0'
            return dict(name='disk'+str(index), node='/dev/disk'+str(index), device=device,
                        sysfs='/sys/devices/disk'+str(index), sysfs_inode=100+index,
                        disk='/sys/devices/disk'+str(index), disk_device=device,
                        diskseq=200+index, partition=0, start=0, sectors=131072,
                        readonly=index == 1, disk_readonly=index == 1,
                        removable=removable, filesystem_uuid=uuid, filesystem='ext4',
                        partuuid='', holders=[], slaves=[], stable=stable,
                        transport='usb-scsi' if removable else 'scsi', partitions=[])
        observed = [disk(1, {'device/wwid':'recovery'}, 'root'),
                    disk(2, {'device/wwid':'source'}, 'source'),
                    disk(3, {'device/wwid':'protected'}, 'protected'),
                    disk(4, {'device/wwid':'usb'}, 'fat', True)]
        loop = dict(device='7:0', sysfs='/sys/devices/virtual/block/loop0', sysfs_inode=70,
                    diskseq=9, backing='/usr.squashfs', backing_identity=[1, 2, 4096],
                    backing_mode=stat.S_IFREG | 0o644, backing_uid=0, backing_gid=0,
                    backing_nlink=1, readonly=True, offset=0, sizelimit=0, sectors=8,
                    holders=[], slaves=[])
        identity = lambda value: dict(stable=value['stable'], partition=0, start=0,
                                      sectors=value['sectors'], filesystem_uuid=value['filesystem_uuid'])
        policy = dict(format_version=2, kind='independent-recovery', protocol=PROTOCOL,
                      writer_model=WRITER_MODEL, envelope_manifest_sha256='2'*64,
                      recovery=identity(observed[0]), source=identity(observed[1]),
                      source_path='/data', media=reviewed_inventory(observed),
                      protected=[dict(role='slot-a', identity=identity(observed[2]))],
                      destinations={'usb':dict(identity=identity(observed[3]),
                                      path='/media/usb', label='Reviewed USB')})
        context = dict(format_version=2, protocol=PROTOCOL, policy_sha256=fingerprint(policy),
                       source='/data', destinations={'usb':dict(path='/media/usb', label='Reviewed USB')})
        provider = MediaProvider(policy, context)
        with patch.object(provider.kernel, 'inventory', return_value=copy.deepcopy(observed)), \
             patch.object(provider.kernel, 'active_loops', return_value=[copy.deepcopy(loop)]):
            initial = provider.complete_inventory()
        self.assertEqual(initial['media'][2]['stable'], {'device/wwid':'protected'})
        changed = copy.deepcopy(observed); changed[2]['diskseq'] += 1
        with patch.object(provider.kernel, 'inventory', return_value=changed), \
             patch.object(provider.kernel, 'active_loops', return_value=[copy.deepcopy(loop)]):
            self.assertNotEqual(provider.complete_inventory(), initial)
        for mutation in ('removal', 'replacement', 'insertion'):
            changed = copy.deepcopy(observed)
            if mutation == 'removal': changed.pop(2)
            elif mutation == 'replacement': changed[2]['stable'] = {'device/wwid':'replacement'}
            else: changed.append(disk(5, {'device/wwid':'unexpected'}, 'extra'))
            with self.subTest(mutation=mutation), \
                 patch.object(provider.kernel, 'inventory', return_value=changed), \
                 patch.object(provider.kernel, 'active_loops', return_value=[copy.deepcopy(loop)]):
                with self.assertRaisesRegex(ValueError, 'topology'):
                    provider.complete_inventory()
        with patch.object(provider.kernel, 'inventory', return_value=copy.deepcopy(observed)), \
             patch.object(provider.kernel, 'active_loops', return_value=[loop, {**loop, 'device':'7:1'}]):
            with self.assertRaisesRegex(ValueError, 'Exactly one'):
                provider.complete_inventory()
        bad_loop = {**loop, 'sectors':9}
        with patch.object(provider.kernel, 'inventory', return_value=copy.deepcopy(observed)), \
             patch.object(provider.kernel, 'active_loops', return_value=[bad_loop]):
            with self.assertRaisesRegex(ValueError, 'extent'):
                provider.complete_inventory()

    def test_ordinary_ab_or_workstation_root_with_marker_cannot_enable_export(self):
        # The old display-service marker says nothing about the actual root.
        # No host block node is opened by these ordinary-root negative tests.
        for filesystem in ('ext4', 'overlay'):
            text = ('1 1 8:1 / / rw - '+filesystem+' /dev/root rw\n'
                    '2 1 0:2 / /proc rw - proc proc rw\n'
                    '3 1 0:3 / /sys ro - sysfs sysfs ro\n')
            provider = MediaProvider(self.policy, self.context)
            with patch.object(provider.kernel, 'mounts', return_value=mount_table(text)), \
                 patch.object(provider.kernel, 'session', return_value={}), \
                 patch.object(provider.kernel, 'block', side_effect=AssertionError('Must not probe host media')):
                with self.assertRaisesRegex(ValueError, 'Recovery root requires consistent ro'):
                    provider.snapshot()

    def test_untrusted_or_symlinked_context_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'context.json';path.write_text('{}');path.chmod(0o644)
            original = os.fstat
            def root_owned(fd):
                # Isolate file validation from the workstation user and /tmp
                # ancestors; actual file modes and no-follow opens remain real.
                info = list(original(fd));info[4] = 0
                if stat.S_ISDIR(info[0]):info[0] = stat.S_IFDIR | 0o755
                return os.stat_result(info)
            with patch('sv08_recovery_media.os.geteuid', return_value=0), patch('sv08_recovery_media.os.fstat', root_owned):
                self.assertEqual(trusted_file(path), b'{}')
                path.chmod(0o666)
                with self.assertRaisesRegex(ValueError, 'Untrusted recovery configuration file'):
                    trusted_file(path)
                path.chmod(0o644)
                link = root / 'linked.json';link.symlink_to(path)
                with self.assertRaises(OSError):trusted_file(link)

    def test_readonly_ordinary_root_marker_cannot_replace_reviewed_image_or_boot_identity(self):
        from contextlib import contextmanager
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name in ('recovery', 'source', 'fat'):(base / name).mkdir()
            (base / 'recovery/etc/sv08').mkdir(parents=True)
            manifest = base / 'recovery/etc/sv08/recovery-image.json'
            manifest.write_text('{"reviewed_fixture_manifest":true}')
            # An apparent legacy marker is present even for the refused A/B root.
            (base / 'recovery/etc/sv08-recovery-image').write_text('present')
            policy_file = base / 'recovery/etc/sv08/recovery-media-policy.json'
            policy_file.write_text('{}')
            paths = {'/':base / 'recovery', '/data':base / 'source', '/media/usb':base / 'fat',
                     '/etc/sv08/recovery-image.json':manifest, str(POLICY):policy_file}
            devices = {'/':os.makedev(8, 1), '/data':os.makedev(8, 2), '/media/usb':os.makedev(8, 3),
                       '/etc/sv08/recovery-image.json':os.makedev(8, 1), str(POLICY):os.makedev(8, 1)}
            held = {}
            @contextmanager
            def fake_open(path, **kwargs):
                key = str(path)
                with opened(paths[key], **kwargs) as fd:
                    held[fd] = key
                    try:yield fd
                    finally:held.pop(fd)
            original = os.fstat
            def information(fd):
                info = original(fd)
                return SimpleNamespace(st_dev=devices[held[fd]], st_ino=info.st_ino,
                                       st_mode=info.st_mode, st_size=info.st_size)
            blocks = {}
            for index, path in enumerate(('/', '/data', '/media/usb'), start=1):
                blocks[path] = dict(stable={'wwid':'reviewed-'+str(index)}, partition=1, start=2048, sectors=131072,
                                    filesystem_uuid='fs-'+str(index), disk='/sys/devices/disk'+str(index),
                                    readonly=index != 3, disk_readonly=index != 3, removable=index == 3)
            policy = {**self.policy, 'image_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                      'recovery':durable_identity(blocks['/']), 'source':durable_identity(blocks['/data']),
                      'system_media':[blocks['/']['stable'], blocks['/data']['stable'], {'wwid':'unmounted-slot-medium'}]}
            context = {**self.context, 'policy_sha256':fingerprint(policy)}
            provider = MediaProvider(policy, context)
            mounts = mount_table('1 1 8:1 / / ro - ext4 /dev/recovery ro,norecovery\n'
                                 '2 1 0:2 / /proc rw - proc proc rw\n'
                                 '3 1 0:3 / /sys ro - sysfs sysfs ro\n'
                                 '4 1 8:2 / /data ro - ext4 /dev/data ro,norecovery\n'
                                 '5 1 8:3 / /media/usb rw - vfat /dev/usb rw\n')
            with patch.object(provider.kernel, 'mounts', return_value=mounts), \
                 patch.object(provider.kernel, 'session', return_value={'test':'measured-session-double'}), \
                 patch.object(provider.kernel, 'block', side_effect=lambda mount, fixture:copy.deepcopy(blocks[mount['path']])), \
                 patch('sv08_recovery_media.opened', fake_open), patch('sv08_recovery_media.os.fstat', information), \
                 patch('sv08_recovery_media.os.fstatvfs', side_effect=lambda fd:SimpleNamespace(f_flag=0 if held[fd] == '/media/usb' else os.ST_RDONLY)), \
                 patch('sv08_recovery_media.Path.read_text', return_value='sv08.recovery='+policy['image_manifest_sha256']) as cmdline:
                self.assertIn('recovery', provider.snapshot())  # Positive control.
                blocks['/media/usb']['stable'] = {'device/wwid':'unmounted-slot-medium', 'device/serial':'extra-attribute'}
                with self.assertRaisesRegex(ValueError, 'shares a system/source medium'):provider.snapshot()
                # Preserve known aliases on either side, regardless of insertion
                # order or which spelling carries the protected value.
                protected = {'wwid':'unmounted-slot-medium'}
                for known_key, other_key in (('wwid', 'device/wwid'), ('device/wwid', 'wwid')):
                    pairs = [(known_key, 'unmounted-slot-medium'), (other_key, 'other-value')]
                    for order in (pairs, list(reversed(pairs))):
                        for side in ('destination', 'inventory'):
                            with self.subTest(known_key=known_key, order=order, side=side):
                                blocks['/media/usb']['stable'] = dict(order) if side == 'destination' else protected
                                policy['system_media'][-1] = protected if side == 'destination' else dict(order)
                                with self.assertRaisesRegex(ValueError, 'shares a system/source medium'):
                                    provider.snapshot()
                usb = {'usb/serial': 'shared-serial',
                       'usb/device': ['1234', '5678', 'shared-serial']}
                for pairs in ([('serial', 'other'), ('device/serial', 'shared-serial')],
                              [('device/serial', 'other'), ('serial', 'shared-serial')]):
                    for order in (pairs, list(reversed(pairs))):
                        for side in ('destination', 'inventory'):
                            with self.subTest(usb_alias=order, side=side):
                                blocks['/media/usb']['stable'] = usb if side == 'destination' else dict(order)
                                policy['system_media'][-1] = dict(order) if side == 'destination' else usb
                                with self.assertRaisesRegex(ValueError, 'shares a system/source medium'):
                                    provider.snapshot()
                policy['system_media'][-1] = protected
                blocks['/media/usb']['stable'] = {'wwid':'reviewed-3'}
                self.assertIn('recovery', provider.snapshot())  # Distinct medium still admitted.
                blocks['/']['filesystem_uuid'] = 'ordinary-readonly-slot-A'
                with self.assertRaisesRegex(ValueError, 'independently reviewed identities'):provider.snapshot()
                blocks['/']['filesystem_uuid'] = 'fs-1'
                blocks['/']['stable'] = {'wwid':'ordinary-workstation-medium'}
                with self.assertRaisesRegex(ValueError, 'independently reviewed identities'):provider.snapshot()
                blocks['/']['stable'] = {'wwid':'reviewed-1'}
                cmdline.return_value = 'root=ordinary-slot-A'
                with self.assertRaisesRegex(ValueError, 'Kernel boot selection'):provider.snapshot()
                cmdline.return_value = 'sv08.recovery='+policy['image_manifest_sha256']+' sv08.recovery=other'
                with self.assertRaisesRegex(ValueError, 'Kernel boot selection'):provider.snapshot()

    def test_installed_controller_keeps_invalid_context_diagnostic_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'missing-registry'
            with patch('sv08_recovery_media.production_adapter', return_value=Unavailable('Untrusted recovery media context')), \
                 patch('sv08_state.Store', return_value=Store(root)):
                status = installed_controller().status()
            self.assertIn('damaged', status['diagnostic'])
            self.assertFalse(status['capabilities']['recovery.export']['available'])
            self.assertIn('Untrusted', status['capabilities']['recovery.export']['reason'])
            self.assertTrue(status['capabilities']['recovery.check']['available'])
            self.assertFalse(root.exists())

    def test_installed_controller_refresh_retries_trust_and_uses_configured_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fallback=root/'fallback';source=root/'configured-source'
            registry=source/'sv08';registry.mkdir(parents=True)
            (registry/'state.json').write_text('distinct damaged configured registry')
            provider=MediaProvider.__new__(MediaProvider);provider.source=source
            provider.capability=lambda action, view:(action == 'recovery.export',
                '' if action == 'recovery.export' else 'Unavailable')
            provider.images=lambda:[]
            provider.destinations=lambda:[{'id':'usb','label':'Reviewed USB'}]
            stores=[]
            def configured_store(path):
                selected=fallback if str(path) == '/data/sv08' else Path(path)
                stores.append(selected)
                return Store(selected)
            with patch('sv08_recovery_media.production_adapter',
                       side_effect=[Unavailable('Another recovery media operation owns admission'),
                                    provider]) as factory, \
                 patch('sv08_state.Store', side_effect=configured_store):
                controller=installed_controller()
                initial=controller.status()
                refreshed=controller.status()
            self.assertEqual(factory.call_count,2)
            self.assertFalse(initial['capabilities']['recovery.export']['available'])
            self.assertIn('Another recovery media operation',
                          initial['capabilities']['recovery.export']['reason'])
            self.assertTrue(refreshed['capabilities']['recovery.export']['available'])
            self.assertEqual(refreshed['destinations'],[{'id':'usb','label':'Reviewed USB'}])
            self.assertEqual(controller.store.root,registry)
            self.assertEqual(stores,[fallback,registry])
            self.assertIn('damaged',refreshed['diagnostic'])
            self.assertEqual((registry/'state.json').read_text(),
                             'distinct damaged configured registry')
            self.assertFalse(fallback.exists())

    def test_injected_recovery_adapter_is_stable_across_status(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=Unavailable('Injected fixture diagnostic')
            controller=RecoveryController(Store(Path(directory)/'missing'),adapter)
            with patch('sv08_recovery_media.production_adapter',
                       side_effect=AssertionError('Injected adapters must not refresh')):
                first=controller.status();second=controller.status()
            self.assertIs(controller.adapter,adapter)
            self.assertEqual(first['capabilities'],second['capabilities'])
            self.assertIn('Injected fixture',
                          second['capabilities']['recovery.export']['reason'])
