import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import sv08_environment_device as device


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.cid = b'0' * 32 + b'\n'
        self.identity = dict(format_version=1, identity_path='/dev/disk/by-path/platform-4022000.mmc',
                             expected_cid_sha256=hashlib.sha256(self.cid).hexdigest())
        self.layout = json.loads((Path(__file__).resolve().parents[1] / 'configs/images/host-ab.json').read_text())
        self.environment = dict(layout_id='ab-8gb-v1', medium='mmc-user-area', size_bytes=65536,
                                copy_offsets_bytes=[4194304, 8388608])
        self.release = dict(deployable=True, devices={p['name']: '/dev/disk/by-partuuid/'+str(i)
                            for i,p in enumerate(self.layout['partitions'],1)})
        self.policy = dict(layout='ab-8gb-v1', image_bytes={'boot':192*1024**2,'rootfs':2048*1024**2})

    def resolve(self, node='mmcblk0', wrong_parent=False, wrong_cid=False, bad_layout=False, bad_gpt=False):
        parent = Path('/sys/devices/platform/4022000.mmc/block') / node
        info = {};offset=16*1024**2
        for i,p in enumerate(self.layout['partitions'],1):
            info[p['name']] = dict(parent=parent, number=f'179:{i}', partition=i,
                                   size=p['mib']*1024**2, start=offset)
            offset += p['mib']*1024**2
        if bad_layout: info['root-a']['start']+=512
        records=[dict(number=x['partition'],name=k,partuuid=self.release['devices'][k].rsplit('/',1)[1],
                      offset_bytes=x['start'],size_bytes=x['size']) for k,x in info.items()]
        if bad_gpt: records[0]['partuuid']='wrong'
        docs = {'environment-device.json':self.identity,'release.json':self.release,'layout.json':self.layout,
                'update-policy.json':self.policy,'environment.json':self.environment}
        def resolve_path(path, strict=False):
            if str(path)==self.identity['identity_path']:return Path('/dev')/node
            if str(path)=='/sys/dev/block/179:2':return parent/(node+'p2')
            if str(path)=='/sys/dev/block/179:0':return parent if not wrong_parent else Path('/sys/other')
            raise AssertionError(path)
        def read_text(path):
            if str(path)=='/proc/cmdline':return 'rauc.slot=A'
            return {'dev':'179:0','removable':'0','size':str(self.layout['image_bytes']//512)}[path.name]
        with patch.object(device,'document',side_effect=lambda p,**kwargs:docs[Path(p).name]), \
             patch('sv08_boot.verify_devices') as verified, \
             patch('sv08_rauc.block_info',side_effect=lambda p:info[next(k for k,v in self.release['devices'].items() if v==p)]) as blocks, \
             patch('sv08_gpt.inspect',return_value={'partition_records':records}) as gpt, \
             patch.object(Path,'resolve',resolve_path),patch.object(Path,'read_text',read_text), \
             patch.object(Path,'read_bytes',return_value=self.cid if not wrong_cid else b'1'*32+b'\n'), \
             patch.object(Path,'lstat',return_value=SimpleNamespace(st_mode=stat.S_IFBLK,st_rdev=os.makedev(179,0))), \
             patch.object(device.os,'stat',return_value=SimpleNamespace(st_dev=os.makedev(179,2))):
            result=device.binding()
            self.assertEqual(blocks.call_count,6)
            verified.assert_called_once_with(self.release,'A')
            self.assertEqual(gpt.call_args.kwargs['environment_regions'],[(4194304,65536),(8388608,65536)])
            return result

    def test_enumeration_change_resolves_same_reviewed_medium(self):
        self.assertEqual(self.resolve('mmcblk2'),Path('/dev/mmcblk2'))
        self.assertEqual(self.resolve('mmcblk0'),Path('/dev/mmcblk0'))

    def test_wrong_parent_cid_geometry_and_gpt_fail_closed(self):
        for failure in ('wrong_parent','wrong_cid','bad_layout','bad_gpt'):
            with self.subTest(failure=failure),self.assertRaises(ValueError):
                self.resolve(**{failure:True})

    def test_wrong_offsets_fail_before_any_device_access(self):
        self.environment['copy_offsets_bytes']=[4194304,8454144]
        with self.assertRaisesRegex(ValueError,'layout'):self.resolve()


def root_owned(method):
    def observed(path, *args, **kwargs):
        entry = list(method(path, *args, **kwargs))
        entry[4] = 0
        return os.stat_result(entry)
    return observed


class WritableMetadataTests(unittest.TestCase):
    def test_normal_recheck_accepts_writable_metadata_but_preparation_stays_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata=Path(tmp)/'identity.json';metadata.write_text('{"format_version": 1}');metadata.chmod(0o644)
            config=Path(tmp)/'fw_env.config';config.write_text(device.content('/dev/mmcblk0'));config.chmod(0o600)
            def flags(path):
                return SimpleNamespace(f_flag=os.ST_RDONLY if Path(path)==config else 0)
            original_document=device.document
            def resolve(*,require_immutable=True):
                original_document(metadata,require_immutable=require_immutable)
                return Path('/dev/mmcblk0')
            with patch.object(Path,'lstat',root_owned(Path.lstat)), \
                 patch.object(device.os,'statvfs',side_effect=flags), \
                 patch.object(device,'binding',side_effect=resolve) as binding:
                self.assertEqual(device.recheck(config),Path('/dev/mmcblk0'))
                binding.assert_called_once_with(require_immutable=False)
                with patch.object(device.os,'geteuid',return_value=0), \
                     patch.object(Path,'stat',root_owned(Path.stat)):
                    with self.assertRaisesRegex(ValueError,'immutable'):
                        device.prepare(config,Path(tmp)/'run',resolve=resolve,
                                       command=lambda *a,**k:self.fail('mount with writable metadata'),
                                       verify=lambda **k:self.fail('CRC with rejected metadata'))
                config.chmod(0o666)
                with self.assertRaisesRegex(ValueError,'map must remain'):
                    device.recheck(config)

    def test_writable_metadata_permissions_and_symlink_still_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'metadata';path.write_text('{}');path.chmod(0o666)
            with patch.object(Path,'lstat',root_owned(Path.lstat)):
                with self.assertRaises(ValueError):device.document(path,require_immutable=False)
                path.chmod(0o644)
                link=Path(tmp)/'link';link.symlink_to(path)
                with self.assertRaises(ValueError):device.document(link,require_immutable=False)


class PublicationTests(unittest.TestCase):
    def test_crc_validation_precedes_readonly_bind_and_rechecks_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'fw_env.config';config.write_text('old');config.chmod(0o644)
            runtime=Path(tmp)/'run';events=[]
            def verify(config):
                self.assertEqual(config.read_text(),device.content('/dev/mmcblk0'))
                self.assertEqual(config.stat().st_mode&0o777,0o600)
                events.append('crc')
            def command(argv,check):
                events.append(argv)
                if argv[1]=='--bind':config.write_text(Path(argv[2]).read_text())
            with patch.object(device.os,'geteuid',return_value=0), \
                 patch.object(device.os,'statvfs',return_value=SimpleNamespace(f_flag=os.ST_RDONLY)), \
                 patch.object(Path,'lstat',root_owned(Path.lstat)), \
                 patch.object(Path,'stat',root_owned(Path.stat)):
                # Ownership is injected; no physical nodes or mount commands are used.
                device.prepare(config,runtime,resolve=lambda:Path('/dev/mmcblk0'),command=command,verify=verify)
            self.assertEqual(events,['crc',['mount','--bind',str(runtime/'fw_env.config'),str(config)],
                                     ['mount','-o','remount,bind,ro',str(config)]])

    def test_publication_rejects_writable_bind_or_changed_binding(self):
        for readonly, changed in ((False, False), (True, True)):
            with self.subTest(readonly=readonly, changed=changed), tempfile.TemporaryDirectory() as tmp:
                config=Path(tmp)/'map';config.write_text('old');config.chmod(0o644)
                runtime=Path(tmp)/'run'
                nodes=iter([Path('/dev/mmcblk0'), Path('/dev/mmcblk2') if changed else Path('/dev/mmcblk0')])
                def command(argv,check):
                    if argv[1]=='--bind':config.write_text(Path(argv[2]).read_text())
                with patch.object(device.os,'geteuid',return_value=0), \
                     patch.object(Path,'lstat',root_owned(Path.lstat)), \
                     patch.object(Path,'stat',root_owned(Path.stat)), \
                     patch.object(device.os,'statvfs',return_value=SimpleNamespace(f_flag=os.ST_RDONLY if readonly else 0)):
                    with self.assertRaisesRegex(ValueError,'read-only'):
                        device.prepare(config,runtime,resolve=lambda:next(nodes),command=command,verify=lambda **k:None)

    def test_rauc_uses_existing_single_dropin_with_prepare_dependency(self):
        repo=Path(__file__).resolve().parents[1]
        import configparser
        config=configparser.ConfigParser();config.read(repo/'configs/host-os/sv08-rauc-service.conf')
        self.assertEqual(config['Unit']['Requires'],'sv08-prepare.service')
        self.assertEqual(config['Unit']['After'],'sv08-prepare.service')
        policy=json.loads((repo/'configs/host-os/rauc-service-policy.json').read_text())
        self.assertEqual([p for p in policy['config_paths'] if '/rauc.service.d/' in p],
                         ['/etc/systemd/system/rauc.service.d/sv08.conf'])

    def test_bad_crc_never_publishes_or_mounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'fw_env.config';config.write_text('old');config.chmod(0o644);runtime=Path(tmp)/'run'
            def reject(**kwargs):raise ValueError('bad CRC')
            with patch.object(device.os,'geteuid',return_value=0), \
                 patch.object(Path,'lstat',root_owned(Path.lstat)), \
                 patch.object(Path,'stat',root_owned(Path.stat)):
                with self.assertRaisesRegex(ValueError,'CRC'):
                    device.prepare(config,runtime,resolve=lambda:Path('/dev/mmcblk0'),verify=reject,
                                   command=lambda *a,**k:self.fail('mount before CRC'))
            self.assertEqual(config.read_text(),'old')
            self.assertFalse((runtime/'fw_env.config').exists())

    def test_default_backend_rechecks_binding_but_temporary_map_does_not(self):
        from sv08_rauc_bootloader import verify_environment_copies, ENV_CONFIG
        with patch.object(device,'recheck',side_effect=ValueError('identity changed')) as check, \
             patch.object(Path,'exists',return_value=True):
            with self.assertRaisesRegex(ValueError,'identity changed'):verify_environment_copies()
            check.assert_called_once_with(ENV_CONFIG)
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'map';config.write_text('bad map')
            with patch.object(device,'recheck') as check:
                with self.assertRaises(ValueError):verify_environment_copies(config)
                check.assert_not_called()
