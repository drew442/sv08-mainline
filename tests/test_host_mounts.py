import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_mounts import apply, BINDS, TMPFS


class OwnerMountTests(unittest.TestCase):
    def test_supported_shadow_bind_is_readonly_before_mode_remount(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('SV08_TEST_ROOT')) as temporary:
            base=Path(temporary);root=base/'root';data=base/'data'
            for source,dest in BINDS.items():
                (data/source).mkdir(parents=True,exist_ok=True);(root/dest).mkdir(parents=True,exist_ok=True)
            for dest in TMPFS: (root/dest).mkdir(parents=True,exist_ok=True)
            (root/'run/sv08').mkdir(parents=True);generation=data/'generations/fixture';generation.mkdir(parents=True)
            source=root/'run/sv08/owner-shadow'
            boot=dict(mode='immutable',generation=str(generation))
            with patch('sv08_mounts.subprocess.run') as run,patch('sv08_owner.prepare_shadow',return_value=source) as prepare:
                run.return_value.returncode=0;apply(root,data,boot,owner_setup=True)
            prepare.assert_called_once_with(root,data)
            commands=[call.args[0] for call in run.call_args_list]
            bind=['mount','--bind',str(source),str(root/'etc/shadow')]
            readonly=['mount','-o','remount,bind,ro',str(root/'etc/shadow')]
            self.assertLess(commands.index(bind),commands.index(readonly))
            self.assertLess(commands.index(readonly),commands.index(['mount','-o','remount,ro',str(root)]))

if __name__=='__main__':unittest.main()
