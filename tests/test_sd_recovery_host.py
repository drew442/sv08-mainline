#!/usr/bin/env python3
"""Focused source/path/root-binding checks; full runtime is a separate VM."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import subprocess

SPEC=importlib.util.spec_from_file_location('sdhost',Path(__file__).resolve().parents[1]/'scripts/build_sd_recovery_host.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

class SDHost(unittest.TestCase):
    def test_gate_binding(self):
        gate=M.gate('a'*64)
        self.assertIn('root=PARTUUID='+M.PARTUUID,gate)
        self.assertIn('unexpected recovery partition index',gate)
        self.assertIn("= '2'",gate)
        self.assertNotIn("= '5'",gate)
        self.assertIn('ro,noload',gate)
        self.assertIn('sha256sum -c etc/sv08/sd-envelope.sha256',gate)
        self.assertIn('switch_root /newroot /sbin/init',gate)
        self.assertNotIn('fw_setenv',gate)
        subprocess.run(['/bin/sh','-n'],input=M.gate('a'*64,'b'*64),text=True,check=True)
        self.assertLess(gate.index('kill \"$watcher\"'),gate.index('exec switch_root'))
    def test_bad_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'source';source.write_text('unapproved')
            with self.assertRaisesRegex(ValueError,'source hash/capacity'):
                M.admitted(source,root/'work')
            linked=root/'linked';linked.symlink_to(source)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                M.safe(linked,True)
            hard=root/'hard';hard.hardlink_to(source)
            with self.assertRaisesRegex(ValueError,'Single-link'):
                M.safe(source,True)
    def test_sidecar_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);build=root/'build';build.mkdir()
            loader=root/'loader';loader.write_text('loader')
            receipt=root/'receipt';receipt.write_text('{}')
            disk=root/'disk.img';sidecar=root/'disk.img.json'
            sidecar.write_text('preserve')
            with self.assertRaisesRegex(ValueError,'Fresh separate'):
                M.assemble(build,loader,receipt,disk,True)
            self.assertEqual(sidecar.read_text(),'preserve')
            self.assertFalse(disk.exists())
            sidecar.unlink();sidecar.symlink_to(receipt)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                M.assemble(build,loader,receipt,disk,True)
            self.assertEqual(receipt.read_text(),'{}')
            self.assertFalse(disk.exists())
    def test_cache_requires_same_supplement(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);primary=root/'primary';primary.write_text('pinned')
            extra=root/'extra';extra.write_text('sudo')
            source=root/'source';namespace={'groups':{'0':{'name':'root'}}}
            record={'owner_namespace':namespace,'additional_package_provenance':{'packages':['sudo']},
                    'inputs':{str(source):M.SOURCE_SHA,str(primary):M.sha(primary),str(extra):M.sha(extra)}}
            M.check_cache(record,source,primary,extra,namespace)
            with self.assertRaisesRegex(ValueError,'supplemental package presence'):
                M.check_cache(record,source,primary,None,namespace)
            extra.write_text('changed')
            with self.assertRaisesRegex(ValueError,'provenance differs'):
                M.check_cache(record,source,primary,extra,namespace)
    def test_capacity_admission(self):
        with self.assertRaisesRegex(ValueError,'Require'):
            M.preflight_space(2*1024**3,False,True)
        self.assertEqual(M.preflight_space(2*1024**3,True,True),1536*1024**2)
        with self.assertRaisesRegex(ValueError,'Require'):
            M.preflight_space(1536*1024**2-1,True,True)
        # Inspection still reports the requirement without allocating anything.
        self.assertEqual(M.preflight_space(0,True,False),1536*1024**2)
    def test_ssh_policy(self):
        conf=(M.CONFIG/'sshd_config').read_text()
        for directive in ('PermitRootLogin no','PasswordAuthentication no','KbdInteractiveAuthentication no','AuthenticationMethods publickey','AllowUsers recovery'):
            self.assertIn(directive,conf)
        service=(M.CONFIG/'sd-host-ssh.service').read_text()
        self.assertNotIn('network-online.target',service)
        self.assertIn('Requires=sd-host-keys.service',service)
    def test_sd_boot_only(self):
        script=M.boot_script(dict.fromkeys(('Image','initrd.img','sv08.dtb'),'b'*64),'a'*64)
        self.assertEqual(script.count('load mmc 0:1'),3)
        for command in ('saveenv','mmc write','fw_setenv','BOOT_A_LEFT','nfsroot'):
            self.assertNotIn(command,script)

if __name__=='__main__':unittest.main()
