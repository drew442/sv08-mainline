import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage_printer',ROOT/'scripts/stage_printer_ui.py');stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)


class StageTests(unittest.TestCase):
    def test_exact_additive_and_restore_historical(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            names={}
            for source,name in [('runtime/sv08_state.py','usr/lib/sv08/sv08_state.py'),('ui/host/index.html','usr/share/cockpit/sv08-host/index.html'),('ui/host/session.js','usr/share/cockpit/sv08-host/session.js'),('ui/host/app.js','usr/share/cockpit/sv08-host/app.js'),('ui/host/manifest.json','usr/share/cockpit/sv08-host/manifest.json')]:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show','8c6f24f^:'+source],cwd=ROOT));p.chmod(0o644);names[name]=None
            for name,raw in [('etc/cockpit/cockpit.conf','[WebService]\nShell=/sv08-host/index.html\n'),('usr/lib/sv08/admin-context.json',json.dumps(dict(format_version=1,context='host')))]:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(raw);p.chmod(0o644);names[name]=None
            parents=set()
            for name in list(names):
                parents.update(str(p) for p in Path(name).parents if str(p)!='.')
            names.update({p:None for p in parents})
            expected=stage.inventory(root,names);before={n:(root/n).read_bytes() for n in names if (root/n).is_file()}
            wrong=json.loads(json.dumps(expected));wrong['usr/lib/sv08/sv08_state.py']['uid']+=1
            with self.assertRaisesRegex(ValueError,'preimage'):stage.stage(root,wrong,True)
            plan=stage.stage(root,expected);self.assertFalse((root/'usr/share/cockpit/sv08-printer').exists());self.assertLess(plan['payload_bytes'],256*1024)
            (root/'usr/share/cockpit/sv08-host/app.js').write_text('wrong')
            with self.assertRaises(ValueError):stage.stage(root,expected,True)
            (root/'usr/share/cockpit/sv08-host/app.js').write_bytes(before['usr/share/cockpit/sv08-host/app.js'])
            plan=stage.stage(root,expected,True)
            self.assertFalse(plan['activated']);self.assertIn('sv08-printer',(root/'usr/share/cockpit/sv08-host/index.html').read_text())
            for name in before:
                if name!='usr/share/cockpit/sv08-host/index.html':self.assertEqual((root/name).read_bytes(),before[name])
            package=root/'usr/share/cockpit/sv08-printer';package.chmod(0o700)
            with self.assertRaisesRegex(ValueError,'Afterimage'):stage.restore(root,plan)
            package.chmod(0o755)
            hostpath=root/'usr/share/cockpit/sv08-host/index.html';hostpath.chmod(0o600)
            with self.assertRaisesRegex(ValueError,'Afterimage'):stage.restore(root,plan)
            hostpath.chmod(0o644)
            stage.restore(root,plan)
            self.assertEqual(stage.inventory(root,names),expected)
            (root/'usr/share/cockpit/sv08-host/index.html').write_bytes((ROOT/'ui/host/index.html').read_bytes())
            (root/'usr/lib/sv08/sv08_state.py').write_bytes((ROOT/'runtime/sv08_state.py').read_bytes())
            (root/'usr/lib/sv08/sv08_data_budget.py').write_bytes((ROOT/'runtime/sv08_data_budget.py').read_bytes());(root/'usr/lib/sv08/sv08_data_budget.py').chmod(0o644)
            names['usr/lib/sv08/sv08_data_budget.py']=None
            current=stage.inventory(root,names)
            missing=dict(current);missing.pop('usr/lib/sv08/sv08_data_budget.py')
            with self.assertRaisesRegex(ValueError,'dependency closure'):stage.stage(root,missing,True,fresh=True)
            fresh=stage.stage(root,current,True,fresh=True)
            self.assertEqual(stage.inventory(root,names),current)
            stage.restore(root,fresh)
    def test_host_delta_and_fixed_helper(self):
        import subprocess
        baseline=subprocess.check_output(['git','show','30a7448:ui/host/index.html'],cwd=ROOT)
        self.assertEqual((ROOT/'ui/host/index.html').read_bytes(),baseline.replace(stage.ANCHOR,stage.ANCHOR+b'\n'+stage.NAV,1))
        source=(ROOT/'runtime/sv08_printer_helper.py').read_text()
        self.assertNotIn('subprocess',source);self.assertNotIn('printer.cfg',source)

if __name__=='__main__':unittest.main()
