import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from definition_repository_template import archive, PREFIX, FILENAME

class TemplateTests(unittest.TestCase):
    def extract(self, directory):
        with ZipFile(BytesIO(archive())) as source:
            source.extractall(directory)
        return Path(directory) / PREFIX.rstrip('/')

    def validate(self, root):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/printer_definitions.py'),
                                 'validate', str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['definitions'], 4)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/printer_definitions.py'),
                                 'preview', str(root), '--installation', str(root/'fixtures/installation.json'),
                                 '--definition', 'my-bed-and-probe'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def helper(self, root):
        return subprocess.run([sys.executable, str(root/'tools/update_catalog.py')],
                              capture_output=True, text=True)

    def test_archive_deterministic_public_allowlist_and_valid(self):
        raw = archive()
        self.assertEqual(raw, archive())
        expected = ['LICENSE', 'README.md', '.gitignore', 'catalog.json',
                    'fixtures/installation.json', 'tools/update_catalog.py',
                    *['definitions/'+name+'.json' for name in ['board','bed','assembly','behaviour']]]
        with ZipFile(BytesIO(raw)) as source:
            self.assertEqual(sorted(source.namelist()), sorted(PREFIX+n for n in expected))
            self.assertTrue(all(i.date_time == (2020,1,1,0,0,0) for i in source.infolist()))
        with tempfile.TemporaryDirectory() as tmp:
            self.validate(self.extract(tmp))

    def test_edit_refreshes_dependency_and_manifest_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.extract(tmp)
            path = root/'definitions/bed.json'
            bed = json.loads(path.read_text());bed['heater_bed']['max_temp']=110
            path.write_text(json.dumps(bed))
            result = self.helper(root);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((root/'definitions/assembly.json').read_text())['extends'],['my-bed','sv08.factory.probe'])
            manifest = json.loads((root/'catalog.json').read_text())
            for row in manifest['definitions']:
                self.assertEqual(row['sha256'],hashlib.sha256((root/row['path']).read_bytes()).hexdigest())
            self.validate(root)

    def test_missing_dependency_and_cycle_leave_files_unchanged(self):
        for kind in ('missing', 'cycle'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root=self.extract(tmp);path=root/'definitions/assembly.json'
                value=json.loads(path.read_text())
                if kind=='missing':value['extends']=['missing-local-base']
                else:value['extends']=[value['id']]
                path.write_text(json.dumps(value))
                before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
                self.assertNotEqual(self.helper(root).returncode,0)
                self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_staging_serves_exact_static_archive(self):
        import stage_printer_ui
        self.assertEqual(stage_printer_ui.payload()['usr/share/cockpit/sv08-printer/'+FILENAME],archive())
