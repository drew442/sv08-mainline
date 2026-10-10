"""Disposable backend fixtures; no host NetworkManager or printer access."""
from contextlib import contextmanager
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_data_budget import fixture_root
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_network import Network, NetworkCertificates, HeldBudget, profile, rows, hosts_named, unique_fields

OLD='11111111-1111-1111-1111-111111111111'
class Budget:
    @contextmanager
    def locked(self): yield self
    def check(self,*args,**kwargs): pass

class Commands:
    def __init__(self): self.calls=[]; self.checkpoint=True; self.fail_up=False; self.fail_reload=False; self.state='inactive'; self.mask='masked'; self.legacy='inactive'; self.legacy_mask='masked'; self.wifi_saved=False
    def __call__(self,*args):
        self.calls.append(args)
        if args[0]=='busctl':
            if args[1]=='get-property': return 's "/etc/NetworkManager/system-connections/original.nmconnection"'
            if 'GetDeviceByIpIface' in args: return 'o "/org/freedesktop/NetworkManager/Devices/1"'
            if 'CheckpointCreate' in args: self.checkpoint=True; return 'o "/org/freedesktop/NetworkManager/Checkpoint/1"'
            if 'CheckpointDestroy' in args:
                if not self.checkpoint: raise ValueError('Network service operation failed; inspect status before retrying')
                self.checkpoint=False; return ''
        if args[0]=='systemctl':
            if 'ActiveState' in args: return self.legacy if 'klipper.service' in args else self.state if 'sv08-klipper.service' in args else 'inactive'
            if 'UnitFileState' in args: return self.legacy_mask if 'klipper.service' in args else self.mask
            if 'stop' in args: self.state='inactive'
            return ''
        if args[0]=='hostnamectl': return ''
        if 'DEVICE,TYPE,STATE,CONNECTION' in args: return 'eth0:ethernet:connected:Original\nwlan0:wifi:disconnected:--'
        if 'GENERAL.CON-UUID,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS' in args: return 'GENERAL.CON-UUID:'+OLD+'\nIP4.ADDRESS[1]:192.0.2.1/24\nIP4.GATEWAY:192.0.2.254\nIP4.DNS[1]:192.0.2.53'
        if 'UUID,NAME,TYPE,DEVICE' in args: return OLD+(':Original:802-11-wireless:wlan0' if self.wifi_saved else ':Original:802-3-ethernet:eth0')
        if 'UUID,FILENAME' in args: return OLD+':/etc/NetworkManager/system-connections/original.nmconnection'
        if '802-11-wireless.ssid,802-11-wireless-security.key-mgmt' in args: return r'802-11-wireless.ssid:home\:wifi'+'\n802-11-wireless-security.key-mgmt:wpa-psk'
        if '802-11-wireless.ssid' in args: return '802-11-wireless.ssid:home wifi'
        if 'ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns' in args: return 'ipv4.method:auto\nipv4.addresses:--\nipv4.gateway:--\nipv4.dns:--'
        if 'GENERAL.DBUS-PATH' in args: return '/org/freedesktop/NetworkManager/Settings/1'
        if 'SSID,SIGNAL,SECURITY,IN-USE' in args: return r'home\:wifi:80:WPA2:*'
        if 'reload' in args and self.fail_reload: raise ValueError('Network service operation failed; inspect status before retrying')
        if 'up' in args and self.fail_up and OLD not in args: raise ValueError('Network service operation failed; inspect status before retrying')
        return ''

class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory(prefix='network-',dir=fixture_root())
        self.addCleanup(self.work.cleanup); self.root=Path(self.work.name)
        self.data=self.root/'data'; (self.data/'system/network-connections').mkdir(parents=True)
        self.etc=self.root/'etc'; self.etc.mkdir(); self.runtime=self.root/'run'; self.runtime.mkdir()
        for base in (self.data/'system',self.etc):
            (base/'hostname').write_text('sv08\n'); (base/'hosts').write_text('127.0.0.1 localhost\n127.0.1.1 sv08 old.alias\n')
        self.boot=self.root/'boot-id'; self.boot.write_text('boot1')
        self.command=Commands(); self.clock=10
        from sv08_state import Store
        self.store=Store(self.data,budget=Budget(),runtime=self.runtime,boot_id=self.boot)
        self.store.initialize()
        self.kernel_names=[]
        self.network=Network(self.data,command=self.command,budget=Budget(),etc=self.etc,runtime=self.runtime,boot_id=self.boot,now=lambda:self.clock,monotonic=lambda:self.clock,set_hostname=self.kernel_names.append)
    def request(self,**updates):
        r=dict(method='apply',device='eth0',kind='ethernet',ssid='',password='',security='open',connection_uuid='',ipv4=dict(method='auto',addresses=[],gateway='',dns=[]),hostname='printer',fqdn='printer.example.test'); r.update(updates); return r
    def apply(self,**updates): return self.network.request(self.request(**updates))
    def test_confirm_persist_names_and_profile(self):
        result=self.apply(); p=self.network.pending(); path=self.data/'system/network-connections'/('sv08-'+p['uuid']+'.nmconnection')
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        self.assertIn('printer.example.test printer sv08 old.alias',(self.etc/'hosts').read_text())
        self.assertEqual(self.network.request(dict(method='confirm',token=result['token'])),dict(confirmed=True))
        self.assertTrue(path.exists()); self.assertIsNone(self.network.pending())
    def test_expired_checkpoint_never_confirms(self):
        result=self.apply(); self.command.checkpoint=False
        with self.assertRaises(ValueError): self.network.request(dict(method='confirm',token=result['token']))
        self.assertIsNotNone(self.network.pending())
    def test_timeout_and_boot_recovery(self):
        self.apply(); self.clock=200; self.network.recover()
        self.assertEqual((self.etc/'hostname').read_text(),'sv08\n'); self.assertFalse(list((self.data/'system/network-connections').iterdir()))
        self.clock=300; self.apply(); self.boot.write_text('boot2'); before=len(self.command.calls); self.network.recover(boot=True)
        self.assertIsNone(self.network.pending()); self.assertEqual(len(self.command.calls),before)
        self.assertEqual(self.kernel_names[-1],b'sv08')
    def test_status_read_only_at_expiry(self):
        self.apply(); self.clock=200; self.network.request(dict(method='status'))
        self.assertIsNotNone(self.network.pending())
    def test_cleanup_failure_retains_journal(self):
        self.apply(); self.command.fail_reload=True
        with self.assertRaises(ValueError): self.network.recover(boot=False) if self.clock>190 else self.network.request(dict(method='rollback',token=self.network.pending()['token']))
        self.assertIsNotNone(self.network.pending())
    def test_activation_failure_repairs(self):
        self.command.fail_up=True
        with self.assertRaises(ValueError): self.apply()
        self.assertIsNone(self.network.pending()); self.assertEqual((self.etc/'hostname').read_text(),'sv08\n')
    def test_name_only_no_candidate_or_device_up(self):
        result=self.network.request(dict(method='apply',kind='name',hostname='printer',fqdn='printer.example.test'))
        self.network.request(dict(method='rollback',token=result['token']))
        self.assertFalse(list((self.data/'system/network-connections').iterdir()))
        self.assertFalse(any('up' in c for c in self.command.calls))
    def test_reuse_private_profile_keeps_original_opaque_credentials(self):
        source=self.data/'system/network-connections/original.nmconnection'
        original='[connection]\nid=Original\nuuid='+OLD+'\ntype=wifi\ninterface-name=wlan0\n[wifi]\nssid=home wifi\n[wifi-security]\nkey-mgmt=wpa-psk\npsk=fixture-secret\n[ipv4]\nmethod=auto\n'
        source.write_text(original); source.chmod(0o600)
        self.apply(device='wlan0',kind='wifi',ssid='home wifi',password='',security='wpa-psk',connection_uuid=OLD)
        self.assertEqual(source.read_text(),original)
        p=self.network.pending(); raw=(source.parent/('sv08-'+p['uuid']+'.nmconnection')).read_text()
        self.assertIn('psk=fixture-secret',raw); self.assertFalse(any('fixture-secret' in str(c) for c in self.command.calls))
        self.assertNotIn('fixture-secret',json.dumps(self.network.status()))
        self.network.request(dict(method='rollback',token=p['token']))
        self.apply(device='wlan0',kind='wifi',ssid='home wifi',password='',security='sae',connection_uuid=OLD)
        p=self.network.pending(); raw=(source.parent/('sv08-'+p['uuid']+'.nmconnection')).read_text()
        self.assertIn('key-mgmt=sae',raw)
    def test_wifi_secret_not_argv_journal_or_status(self):
        self.apply(device='wlan0',kind='wifi',ssid='home:wifi',password='fixture-secret',security='wpa-psk')
        self.assertNotIn('fixture-secret',json.dumps(self.command.calls)+json.dumps(self.network.pending())+json.dumps(self.network.status()))
        self.assertEqual(self.network.request(dict(method='wifi.scan',device='wlan0'))['networks'][0]['ssid'],'home:wifi')
    def test_validation_before_mutation(self):
        for r in (self.request(ipv4=dict(method='manual',addresses=[],gateway='',dns=[])),self.request(hostname='bad.name'),self.request(device='--option'),self.request(password='secret')):
            with self.assertRaises(ValueError): self.network.request(r)
        self.assertIsNone(self.network.pending()); self.assertFalse(any('CheckpointCreate' in c or 'up' in c or 'hostnamectl' in c for c in self.command.calls))
    def test_restart_masked_or_atomic_only(self):
        root_patch=patch('sv08_admission.os.geteuid',return_value=0); root_patch.start(); self.addCleanup(root_patch.stop)
        self.assertTrue(self.network.request(dict(method='restart',confirm=True))['restarting'])
        (self.runtime/'shutdown.json').unlink()
        self.command.mask='enabled'
        with self.assertRaises(ValueError): self.network.request(dict(method='restart',confirm=True))
        self.command.state='active'; self.command.legacy='active'
        with self.assertRaises(ValueError): self.network.request(dict(method='restart',confirm=True))
        self.command.legacy='inactive'
        from sv08_admission import Admission
        quiesced=[]
        with patch('sv08_admission.Admission',side_effect=lambda *args,**kwargs: Admission(*args,request=lambda path:quiesced.append(path),**kwargs)):
            self.assertTrue(self.network.request(dict(method='restart',confirm=True))['restarting'])
        self.assertEqual(len(quiesced),1)
        self.assertFalse(any(c[:2]==('systemctl','start') for c in self.command.calls))
        (self.runtime/'shutdown.json').unlink()
        self.command.state='active'; self.command.calls.clear()
        def refuse(path): raise ValueError('Printer busy')
        with patch('sv08_admission.Admission',side_effect=lambda *args,**kwargs: Admission(*args,request=refuse,**kwargs)):
            with self.assertRaises(ValueError): self.network.request(dict(method='restart',confirm=True))
        self.assertFalse(any('reboot' in c or 'stop' in c for c in self.command.calls))

    def test_delayed_reboot_keeps_new_admission_closed(self):
        # Command fixture acknowledges queueing but never performs shutdown.
        # This reproduces the interval after --no-block returns, offline.
        from sv08_admission import Admission
        from test_service_admission import Services
        services = Services()
        services.states = {name: 'inactive' for name in services.states}
        with patch('sv08_admission.os.geteuid', return_value=0):
            self.network.request(dict(method='restart', confirm=True))
            with self.assertRaisesRegex(ValueError, 'restart|shutdown'):
                with Admission(self.runtime, systemd=services, boot_id=self.boot)():
                    self.fail('New operation admitted after reboot was queued')

    def test_successful_queue_keeps_injected_printer_services_stopped(self):
        from sv08_admission import Admission
        from test_service_admission import Services
        services = Services()
        self.network.admission = Admission(self.runtime, services, lambda path: None, boot_id=self.boot)
        with patch('sv08_admission.os.geteuid', return_value=0):
            self.network.request(dict(method='restart', confirm=True))
        self.assertEqual(set(services.states.values()), {'inactive'})
        self.assertFalse(any(action == 'start' for action, name in services.calls))

    def test_failed_queue_clears_intent_restores_services_and_allows_retry(self):
        from sv08_admission import Admission
        from test_service_admission import Services
        services = Services()
        self.network.admission = Admission(self.runtime, services, lambda path: None, boot_id=self.boot)
        original = self.command
        def command(*args):
            if args == ('systemctl', '--no-block', 'reboot'):
                raise FileNotFoundError('Reboot command could not launch')
            return original(*args)
        self.network.command = command
        with patch('sv08_admission.os.geteuid', return_value=0):
            with self.assertRaisesRegex(FileNotFoundError, 'could not launch'):
                self.network.request(dict(method='restart', confirm=True))
            self.assertFalse((self.runtime/'shutdown.json').exists())
            self.assertEqual(set(services.states.values()), {'active'})
            self.network.command = original
            self.network.request(dict(method='restart', confirm=True))
        self.assertEqual(set(services.states.values()), {'inactive'})

    def test_lost_reboot_acknowledgment_keeps_services_stopped_and_writers_blocked(self):
        from sv08_admission import Admission
        from sv08_restart import start_admitted
        from sv08_state import Store
        from test_service_admission import Services
        original=self.command
        # A transport timeout or completed command error cannot establish that
        # systemd did not accept the request before the reply was lost.
        for error in (subprocess.TimeoutExpired(['systemctl','reboot'],40), ValueError('Reply lost')):
            with self.subTest(error=type(error).__name__):
                services=Services()
                self.network.admission=Admission(self.runtime,services,lambda path:None,boot_id=self.boot)
                def command(*args):
                    if args==('systemctl','--no-block','reboot'): raise error
                    return original(*args)
                self.network.command=command
                with patch('sv08_admission.os.geteuid',return_value=0):
                    with self.assertRaisesRegex(ValueError,'uncertain.*closed'):
                        self.network.request(dict(method='restart',confirm=True))
                    self.assertTrue((self.runtime/'shutdown.json').exists())
                    self.assertEqual(set(services.states.values()),{'inactive'})
                    self.assertFalse(any(action=='start' for action,name in services.calls))
                    with self.assertRaisesRegex(ValueError,'shutdown'), Admission(self.runtime,services,boot_id=self.boot)(): pass
                    with self.assertRaisesRegex(ValueError,'shutdown'), start_admitted(self.runtime,self.boot): pass
                    store=Store(self.data,budget=self.network.budget,runtime=self.runtime,boot_id=self.boot)
                    with self.assertRaisesRegex(ValueError,'shutdown'): store.policy(mode='writable')
                (self.runtime/'shutdown.json').unlink()

    def test_intent_no_space_does_not_queue_reboot_and_restores_services(self):
        import errno
        from sv08_admission import Admission
        from test_service_admission import Services
        services = Services()
        self.network.admission = Admission(self.runtime, services, lambda path: None, boot_id=self.boot)
        with patch('sv08_admission.os.geteuid', return_value=0), patch('sv08_state.atomic_json', side_effect=OSError(errno.ENOSPC, 'No space')):
            with self.assertRaises(OSError): self.network.request(dict(method='restart', confirm=True))
        self.assertFalse((self.runtime/'shutdown.json').exists())
        self.assertEqual(set(services.states.values()), {'active'})
        self.assertFalse(any('reboot' in call for call in self.command.calls))

    def test_restart_refuses_state_writer_and_pending_network_rollback(self):
        with self.store.locked(), self.assertRaisesRegex(ValueError, 'busy'):
            self.network.request(dict(method='restart', confirm=True))
        self.assertEqual(self.command.calls, [])
        self.apply()
        self.clock = 200  # Expired rollback is still an outstanding operation.
        with self.assertRaisesRegex(ValueError, 'network changes'):
            self.network.request(dict(method='restart', confirm=True))
        self.assertIsNotNone(self.network.pending())
        self.assertFalse(any('reboot' in call for call in self.command.calls))

    def test_public_wifi_metadata_and_duplicate_request_rejection(self):
        self.command.wifi_saved=True
        result=self.network.request(dict(method='status'))
        saved=result['connections'][0]
        self.assertEqual(saved['ssid'],'home:wifi'); self.assertEqual(saved['security'],'wpa-psk')
        self.assertEqual(saved['type'],'wifi'); self.assertEqual(saved['ipv4']['addresses'],[])
        self.assertEqual(saved['ipv4']['dns'],[]); self.assertEqual(saved['ipv4']['gateway'],'')
        self.assertFalse(any('psk' in str(c) for c in self.command.calls))
        with self.assertRaises(ValueError): json.loads('{"method":"status","method":"apply"}',object_pairs_hook=unique_fields)
        with self.assertRaises(ValueError): json.loads('{"ipv4":{"method":"auto","method":"manual"}}',object_pairs_hook=unique_fields)

    def test_hosts_custom_mapping_and_escaping(self):
        with self.assertRaises(ValueError): hosts_named('192.0.2.1 printer\n','printer','')
        self.assertEqual(rows(r'a\:b:c\\d'),[['a:b','c\\d']])

    def test_certificate_failure_rolls_back_network(self):
        def fail(p,r): raise ValueError('Certificate reconciliation failed')
        self.network.post_apply=fail
        with self.assertRaisesRegex(ValueError,'Certificate'): self.apply()
        self.assertIsNone(self.network.pending()); self.assertEqual(self.kernel_names[-1],b'sv08')

    def test_corrupt_journal_refuses_actions_before_any_restore(self):
        self.apply(); p=self.network.pending(); p['uuid']='../unrelated'
        self.network.journal(p); before=len(self.command.calls); names_before=list(self.kernel_names)
        with self.assertRaisesRegex(ValueError,'rollback journal'): self.network.recover(boot=True)
        self.assertEqual(len(self.command.calls),before); self.assertEqual(self.kernel_names,names_before)
        self.assertTrue((self.network.root/'pending.json').exists())

    def test_network_certificates_preserve_authority_and_both_old_new_names(self):
        import subprocess
        from sv08_identity import Identity
        from test_data_budget import fixture_budget
        keys=self.data/'users/sv08/.ssh'; keys.mkdir(parents=True)
        key=self.root/'test-key'
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
        (keys/'authorized_keys').write_text(key.with_suffix('.pub').read_text())
        self.data.chmod(0o700)
        budget=fixture_budget(self.data)
        identity=Identity(self.data,os.getuid(),os.getgid(),os.getuid(),budget=budget)
        initial=identity.ensure(['sv08','192.0.2.1'])
        identity.budget=HeldBudget(budget)
        certificates=NetworkCertificates(self.network,identity=identity,discover=lambda data:['printer.example.test','192.0.2.50'],publish=lambda identity:True)
        with budget.locked():
            certificates.prepare({},self.request(ipv4=dict(method='manual',addresses=['192.0.2.40/24'],gateway='',dns=[])))
            certificates.activate({},self.request())
        result=identity.request({'method':'status'})
        self.assertEqual(initial['ca_fingerprint'],result['ca_fingerprint'])
        self.assertEqual(initial['ssh_fingerprint'],result['ssh_fingerprint'])
        for name in ['DNS:sv08','DNS:printer','DNS:printer.local','DNS:printer.example.test','IP:192.0.2.1','IP:192.0.2.40','IP:192.0.2.50']:
            self.assertIn(name,result['service_names'])

if __name__=='__main__': unittest.main()
