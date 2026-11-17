import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_preflight import check

class Prerequisites(unittest.TestCase):
    def test_refusal_collects_missing_tools_bytes_and_inodes_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'new/work'
            with patch('build_preflight.shutil.which',return_value=None),patch('build_preflight.os.statvfs',return_value=SimpleNamespace(f_bavail=100,f_frsize=1,f_favail=0,f_flag=0)):
                with self.assertRaisesRegex(ValueError,'missing tools.*free bytes.*free inodes'):
                    check(output,tools=['missing'],min_bytes=101,min_inodes=1)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_exact_floors_and_private_mount_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            for flags in [getattr(os,'ST_NOEXEC',8),getattr(os,'ST_NODEV',4),getattr(os,'ST_RDONLY',1)]:
                with patch('build_preflight.os.statvfs',return_value=SimpleNamespace(f_bavail=10,f_frsize=4096,f_favail=20,f_flag=flags)):
                    with self.assertRaises(ValueError):check(directory,min_bytes=40960,min_inodes=20,device_nodes=True)
            with patch('build_preflight.os.statvfs',return_value=SimpleNamespace(f_bavail=10,f_frsize=4096,f_favail=20,f_flag=0)):
                self.assertEqual(check(directory,min_bytes=40960,min_inodes=20)['free_inodes'],20)

    def test_symlink_and_invalid_resource_floors_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            link=Path(directory)/'link';link.symlink_to(directory,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):check(link/'output')
            for value in [-1,True,1.5]:
                with self.assertRaises(ValueError):check(directory,min_bytes=value)

    def test_existing_cli_refuses_before_output_or_stage_mutation(self):
        import importlib
        import io
        from contextlib import redirect_stdout
        for module, args, stage in [
            ('recovery_image',['assemble','--work','/unused/output','--execute'],'assemble'),
            ('prepare_host_os',['--stage','bootstrap','--work','build/preflight-test','--execute'],'bootstrap')]:
            m=importlib.import_module(module)
            with patch('sys.argv',[module,*args]),patch('build_preflight.check',side_effect=ValueError('fixture missing prerequisite')) as guard,patch.object(m,stage) as mutation,patch('os.geteuid',return_value=0),redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError,'missing prerequisite'):m.main()
                guard.assert_called_once();mutation.assert_not_called()
