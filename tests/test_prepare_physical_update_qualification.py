"""Small offline contract tests; never creates filesystem images or contacts hardware."""
import ast
import copy
import inspect
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import prepare_physical_update_qualification as composer


def identity():
    board=json.loads((REPO/'configs/host-os/recovery-test-sv08-01.json').read_text())
    layout=json.loads((REPO/'configs/images/host-ab.json').read_text())
    return dict(format_version=1, context=composer.CONTEXT, hardware_profile='test-sv08-01',
                board_mmc_device_index=1, environment_device='/dev/mmcblk2', environment_by_path='/dev/disk/by-path/platform-4022000.mmc', kernel_release=board['kernel_release'],
                devices={p['role']:'/dev/disk/by-partuuid/'+p['partuuid'] for p in board['partitions']},
                compatible='sv08-test-sv08-01', klipper_commit='f0892d82b0f1c1228454f09eb508eddde2250f4b',
                layout='ab-8gb-v1', image_bytes=layout['image_bytes'],
                partition_bytes={p['name']:p['mib']*1024**2 for p in layout['partitions']})


class PhysicalComposerTests(unittest.TestCase):
    def test_explicit_identity_and_geometry(self):
        profile=identity()
        composer.profile_check(profile)
        for field, value in [('board_mmc_device_index', None), ('board_mmc_device_index', True),
                             ('environment_device','/dev/mmcblk1'), ('environment_device','/dev/disk/by-path/platform-4022000.mmc'),
                             ('environment_by_path',None), ('kernel_release','unknown'), ('context','qemu'),
                             ('image_bytes',8*1024**3), ('compatible','sv08-offline-test-only')]:
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                bad=copy.deepcopy(profile);bad[field]=value;composer.profile_check(bad)
        for role in profile['devices']:
            bad=copy.deepcopy(profile);bad['devices'][role]='/dev/mmcblk1p1'
            with self.assertRaises(ValueError): composer.profile_check(bad)
        bad=copy.deepcopy(profile);bad['partition_bytes']['data']+=1024**2
        with self.assertRaises(ValueError): composer.profile_check(bad)

    def root(self, directory):
        root=Path(directory)
        (root/'etc/systemd/system').mkdir(parents=True)
        for unit in ('rauc', 'sv08-boot-health'):
            (root/'etc/systemd/system'/ (unit+'.service')).symlink_to('/dev/null')
        return root

    def test_real_backend_configuration_and_masks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=self.root(temp)
            manifest,policy=composer.configure(root,identity(),'qualification-healthy',2,{},False)
            self.assertTrue(manifest['deployable']);self.assertTrue(manifest['test_only'])
            self.assertEqual(manifest['release_revision'],2)
            self.assertEqual(policy['image_bytes'],composer.SIZES)
            self.assertEqual((root/'etc/fw_env.config').read_text(),
                             '/dev/mmcblk2 0x400000 0x10000\n/dev/mmcblk2 0x800000 0x10000\n')
            for unit in composer.MASKS:
                self.assertEqual(os.readlink(root/'etc/systemd/system'/(unit+'.service')),'/dev/null')
            for unit in ('rauc','sv08-boot-health'):
                self.assertFalse((root/'etc/systemd/system'/(unit+'.service')).is_symlink())
            sys.path.insert(0,str(REPO/'runtime'))
            from sv08_rauc import validate_config
            validate_config((root/'etc/rauc/system.conf').read_text(),manifest,policy,
                            Path('/etc/rauc/release-keyring.pem'))
            self.assertFalse((root/'usr/lib/sv08/qualification-bin').exists())

    def test_environment_backend_refuses_identity_symlink_without_weakening_guard(self):
        sys.path.insert(0,str(REPO/'runtime'))
        from sv08_rauc_bootloader import verify_environment_copies
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); node=root/'canonical';node.write_bytes(b'public incomplete environment fixture')
            alias=root/'identity-by-path';alias.symlink_to(node)
            config=root/'fw_env.config'
            def map_for(path):
                config.write_text(str(path)+' 0x400000 0x10000\n'+str(path)+' 0x800000 0x10000\n')
            map_for(node)
            with self.assertRaisesRegex(ValueError,'unreadable or has a bad CRC'):
                verify_environment_copies(config)
            map_for(alias)
            with self.assertRaises(OSError) as rejected:
                verify_environment_copies(config)
            self.assertEqual(rejected.exception.errno,errno.ELOOP)

    def test_account_binding_blocks_consumers_if_seed_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=self.root(temp)
            composer.configure(root,identity(),'healthy',2,{},False)
            unit=(root/'etc/systemd/system/sv08-qualification-account.service').read_text()
            self.assertIn('Requires=sv08-prepare.service\nAfter=sv08-prepare.service',unit)
            self.assertIn('ExecStart=/usr/bin/mount --bind /data/sv08/system/qualification-account-shadow /etc/shadow',unit)
            self.assertNotIn('ConditionPathExists',unit)
            self.assertNotIn('-',unit.split('ExecStart=')[1].split('/usr/bin/mount')[0])
            for consumer in ('sv08-identity.service','ssh.service','cockpit.socket','cockpit.service'):
                dependency=(root/'etc/systemd/system'/(consumer+'.d')/'qualification-account.conf').read_text()
                self.assertIn('Requires=sv08-qualification-account.service',dependency)
                self.assertIn('After=sv08-qualification-account.service',dependency)
            self.assertFalse((root/'data/sv08/system/qualification-account-shadow').exists())

    def test_unhealthy_changes_only_health_observation_and_version(self):
        with tempfile.TemporaryDirectory() as healthy, tempfile.TemporaryDirectory() as unhealthy:
            h=self.root(healthy);u=self.root(unhealthy)
            composer.configure(h,identity(),'healthy',2,{},False)
            composer.configure(u,identity(),'unhealthy',3,{},True)
            changed=[]
            for path in u.rglob('*'):
                if path.is_file() and not path.is_symlink():
                    rel=path.relative_to(u); counterpart=h/rel
                    if not counterpart.exists() or counterpart.read_bytes()!=path.read_bytes(): changed.append(str(rel))
            self.assertEqual(sorted(changed),sorted(['usr/lib/sv08/release.json',
                'usr/lib/sv08/qualification-bin/systemctl',
                'etc/systemd/system/sv08-boot-health.service.d/qualification.conf']))
            wrapper=u/'usr/lib/sv08/qualification-bin/systemctl'
            failed=subprocess.run([sys.executable,str(wrapper),'is-active','sv08-prepare.service'],capture_output=True,text=True)
            self.assertEqual((failed.returncode,failed.stdout),(3,'inactive\n'))
            forwarded=subprocess.run([sys.executable,str(wrapper),'--version'],capture_output=True)
            actual=subprocess.run(['/usr/bin/systemctl','--version'],capture_output=True)
            self.assertEqual((forwarded.returncode,forwarded.stdout),(actual.returncode,actual.stdout))

    def test_staging_refuses_symlink_parent(self):
        with tempfile.TemporaryDirectory() as rootdir, tempfile.TemporaryDirectory() as outside:
            root=Path(rootdir);(root/'usr').symlink_to(outside)
            with self.assertRaises(ValueError): composer.configure(root,identity(),'healthy',2,{},False)
            self.assertEqual(list(Path(outside).iterdir()),[])

    def test_public_copy_excludes_source_authentication_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); source=base/'public'; (source/'etc/ssh').mkdir(parents=True)
            (source/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\nsv08:x:1000:1000::/home/sv08:/bin/bash\n')
            for rel in ('etc/shadow','etc/gshadow','etc/ssh/ssh_host_ed25519_key','home/sovol/.ssh/authorized_keys'):
                path=source/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('excluded fixture content')
            target=base/'copy';composer.copy_public_root(source,target)
            self.assertEqual((target/'etc/shadow').read_text(),'root:*:0:0:99999:7:::\nsv08:*:0:0:99999:7:::\n')
            self.assertEqual((target/'etc/shadow').stat().st_mode & 0o777,0o600)
            for rel in ('etc/gshadow','etc/ssh/ssh_host_ed25519_key','home/sovol/.ssh'):
                self.assertFalse((target/rel).exists())

    def test_composer_stages_printer_payload_before_host_ui(self):
        tree=ast.parse(inspect.getsource(composer.compose))
        calls=sorted((node.lineno,node.func.id) for node in ast.walk(tree)
                     if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
                     and node.func.id in ('stage_printer_capabilities','admin_stage'))
        self.assertEqual([name for _,name in calls],['stage_printer_capabilities','admin_stage'])

    def test_public_printer_payload_preserves_backend_and_composes_pages(self):
        from stage_admin_ui import compose_host
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); runtime=root/'usr/lib/sv08';runtime.mkdir(parents=True)
            for source in (REPO/'runtime').glob('*.py'): (runtime/source.name).write_bytes(source.read_bytes())
            receipt=composer.stage_printer_capabilities(root)
            self.assertIn('usr/share/cockpit/sv08-printer/app.js',receipt)
            html=compose_host((REPO/'ui/host/index.html').read_bytes()).decode()
            for page in ('printer','printer-connections','definitions','definition-sources'):
                self.assertIn('data-page="'+page+'"',html)
            bad=runtime/'sv08_printer_helper.py';bad.write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError,'backend differs'):
                composer.stage_printer_capabilities(root)

    def test_dry_run_does_not_create_output(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);boardroot=base/'board';boardroot.mkdir()
            config=identity();(base/'profile.json').write_text(json.dumps(config))
            for name in ('rauc.deb','keyring.pem','owner.pub','ca.pem'): (base/name).write_text('public fixture\n')
            (base/'feed.json').write_text(json.dumps(dict(format_version=1,url='https://example.test/feed/',channel='stable',ca_file='/public/ca',signer_ca_file='/public/keyring')))
            (boardroot/'etc').mkdir()
            (boardroot/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\nsv08:x:1000:1000::/home/sv08:/bin/bash\n')
            runtime=boardroot/'usr/lib/sv08';runtime.mkdir(parents=True)
            (runtime/'release.json').write_text(json.dumps(dict(release='source',release_revision=1,state_schema=1,deployable=False,devices=config['devices'])))
            package=boardroot/'usr/share/doc/sv08-klipper';package.mkdir(parents=True)
            (package/'release.json').write_text(json.dumps(dict(source_commit=config['klipper_commit'])))
            board=composer.profile_check(config)
            for role in ('image','dtb'):
                path=boardroot/board['artifacts'][role]['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
            (boardroot/('boot/initrd.img-'+board['kernel_release'])).write_bytes(b'fixture')
            a=Namespace(board_root=boardroot,profile=base/'profile.json',rauc_deb=base/'rauc.deb',keyring=base/'keyring.pem',owner_key=base/'owner.pub',feed_config=base/'feed.json',tls_ca=base/'ca.pem',work=base/'output',context=composer.CONTEXT,healthy_release='healthy',unhealthy_release='unhealthy',execute=False,validation_dictionary=None)
            with patch.object(composer,'sha',side_effect=lambda p:next((v['sha256'] for v in board['artifacts'].values() if v.get('path')==str(p.relative_to(boardroot))), 'unused')), patch.object(composer.subprocess,'check_output',return_value='Package: rauc\nVersion: 1.15.2-0sv08.2\nArchitecture: arm64\n'), patch.object(composer,'run') as run:
                result=composer.compose(a)
            self.assertFalse(a.work.exists());run.assert_not_called()
            self.assertEqual([r['revision'] for r in result['releases']],[2,3])
            self.assertFalse(result['signed'])


if __name__ == '__main__': unittest.main()
