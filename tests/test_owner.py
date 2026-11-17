import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_owner import Owner, prepare_shadow, shadow_text, validate_password
from sv08_web import password_hash

PASSWORD = 'private fixture password'


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('SV08_TEST_ROOT'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); (self.root/'system').mkdir(mode=0o700)
        self.owner = Owner(self.root, os.getuid())

    def enroll(self): self.owner.save(PASSWORD, PASSWORD, self.owner.status())

    def test_private_enrollment_explicit_rotation_and_stale_review(self):
        before = self.owner.status(); self.enroll()
        record = self.root/'system/owner.json'; raw = record.read_bytes()
        self.assertEqual(record.stat().st_mode & 0o777, 0o600)
        public = self.owner.status(); self.assertNotIn('password_hash', public)
        self.assertNotIn(PASSWORD.encode(), raw)
        with self.assertRaisesRegex(ValueError, 'changed'): self.owner.save(PASSWORD,PASSWORD,before)
        with self.assertRaisesRegex(ValueError, 'explicit'): self.owner.save(PASSWORD,PASSWORD,public)
        self.assertEqual(record.read_bytes(), raw)
        self.owner.save('replacement fixture', 'replacement fixture', public, reset=True)
        self.assertNotEqual(self.owner.status()['enrollment'],public['enrollment'])
        with self.assertRaisesRegex(ValueError,'changed'): self.owner.save(PASSWORD,PASSWORD,public,reset=True)

    def test_password_policy_and_stdin(self):
        for password in ('a'*11, 'a'*257, 'a'*12+'\n', 'a'*12+'\r','a'*12+'\x00','unicode-é'*2):
            with self.assertRaises(ValueError): validate_password(password,password)
        for password in (' '*12,'a'*256): validate_password(password,password)
        with self.assertRaisesRegex(ValueError,'match'): validate_password(PASSWORD, 'other')
        with patch('sv08_web.subprocess.run') as run:
            run.return_value.returncode=0; run.return_value.stdout='$6$fixture$'+'a'*86
            password_hash(PASSWORD)
            self.assertNotIn(PASSWORD, str(run.call_args.args)); self.assertEqual(run.call_args.kwargs['input'],PASSWORD+'\n')

    def test_malformed_permissions_links_and_failed_recheck_preserve_record(self):
        self.enroll(); path=self.root/'system/owner.json'; original=path.read_bytes()
        def fail(): raise ValueError('media changed')
        with self.assertRaisesRegex(ValueError,'media changed'):
            self.owner.save(PASSWORD,PASSWORD,self.owner.status(),True,fail)
        self.assertEqual(path.read_bytes(),original); self.assertEqual(len(list(path.parent.iterdir())),1)
        path.chmod(0o644)
        with self.assertRaises(ValueError): self.owner.status()
        path.chmod(0o600); path.write_bytes(b'{broken')
        with self.assertRaisesRegex(ValueError,'no repair'): self.owner.status()
        self.assertEqual(path.read_bytes(),b'{broken')
        path.unlink(); path.symlink_to(self.root/'absent')
        with self.assertRaises(OSError): self.owner.status()
        path.unlink(); (self.root/'system').rename(self.root/'real-system'); (self.root/'system').symlink_to('real-system')
        with self.assertRaises(OSError): self.owner.status()

    def test_slot_shadow_preserves_other_accounts_and_lock_without_owner(self):
        passwd='root:x:0:0::/root:/bin/bash\nsv08:x:1000:1000::/home/sv08:/bin/bash\n'
        shadow='root:*:1:2:3:4:5:6:7\nsv08:*:0:0:99999:7:::\ndaemon:!:10:0:99999:7:::\n'
        self.enroll(); hashed=self.owner.load()[0]['password_hash']
        for slot in ('A','B'):
            root=self.root/slot; (root/'etc').mkdir(parents=True); (root/'run').mkdir()
            (root/'etc/shadow').write_text(shadow); (root/'etc/passwd').write_text(passwd)
            result=prepare_shadow(root,self.root,os.getuid())
            self.assertEqual(result.read_text(),shadow.replace('sv08:*:', 'sv08:'+hashed+':'))
            self.assertEqual((root/'etc/shadow').read_text(),shadow)
            self.assertEqual(result.stat().st_mode & 0o777,0o600)
        self.assertEqual(shadow_text(shadow.replace('sv08:*:', 'sv08:unexpected:'),passwd,None),shadow)
        with self.assertRaises(ValueError): shadow_text(shadow,passwd.replace(':1000:1000:',':1001:1000:'),hashed)

if __name__ == '__main__': unittest.main()
