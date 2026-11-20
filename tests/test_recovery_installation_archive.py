# SPDX-License-Identifier: AGPL-3.0-or-later
"""Synthetic offline fixtures; fake reader does NOT measure native image binding."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_recovery_installation_archive import prepare, contents, image_manifest, retained_system
from sv08_export import Export
from sv08_restore import Restore
from sv08_state import Store
from sv08_recovery_activation import compatible
from test_data_budget import fixture_root

REVISION = '1'*40
SOURCE = dict(slot='B', release='legacy', state_schema=1, release_revision=2)
TARGET = dict(slot='A', release='supported', state_schema=1, release_revision=4)


@contextmanager
def local_admission(unused):
    # Fixture export only; production preparation uses checked local directories.
    yield None


class InstallationArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=fixture_root())
        self.root = Path(self.tmp.name)
        self.data = self.root/'data'; self.data.mkdir(mode=0o700)
        self.store = Store(self.data/'sv08'); self.store.initialize()
        boot = self.store.prepare_boot('B', 'legacy', 1, 2)
        self.generation = Path(boot['generation'])
        self.source = dict(SOURCE, generation=self.generation.name)
        (self.generation/'config/printer.cfg').write_bytes(b'user config and calibration\n')
        os.chmod(self.generation/'config/printer.cfg', 0o640)
        if os.geteuid() == 0: os.chown(self.generation/'config/printer.cfg', 1234, 1235)
        (self.generation/'ui/settings').write_bytes(b'custom application settings')
        state = self.store.load()
        state['owner_policy_note'] = 'preserve arbitrary policy records'
        state['slots']['A'] = dict(state['slots']['B'])
        self.store.save(state)
        self.old_assignment = dict(format_version=1, release='legacy', host_klipper_commit='2'*40, definitions=[])
        (self.generation/'mcu-firmware.json').write_text(json.dumps(self.old_assignment))
        (self.store.root/'system/machine-id').write_text('a'*32+'\n')
        for relative, payload, mode in (('system/ssh/ssh_host_fixture_key', b'fake SSH identity', 0o600),
                                        ('system/cockpit/ws-certs.d/fixture.cert', b'fake owner CA', 0o640),
                                        ('shared/gcodes/user-setting', b'shared application value', 0o640)):
            path = self.store.root/relative
            path.write_bytes(payload); path.chmod(mode)
        (self.store.root/'system/klipper-start.json').write_bytes(b'exact old commissioning permission')
        identity = self.store.root/'system/identity'; (identity/'generations'/('b'*32)).mkdir(parents=True)
        (identity/'generations'/('b'*32)/'owner').write_bytes(b'opaque identity fixture')
        (identity/'current').symlink_to('generations/'+'b'*32)
        (self.store.root/'shared/logs/README').symlink_to('../../usr/share/doc/systemd/README.logs')
        # WAL bytes copied from a synthetic live DB then quiesced before export.
        db = self.root/'fixture.db'; connection = sqlite3.connect(db)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA wal_autocheckpoint=0')
        connection.execute('CREATE TABLE calibration (id INTEGER PRIMARY KEY, value TEXT)')
        connection.execute("INSERT INTO calibration VALUES (1, 'retained committed row')")
        connection.commit()
        for suffix in ('', '-wal', '-shm'):
            shutil.copyfile(Path(str(db)+suffix), self.generation/('database/app.db'+suffix))
        connection.close()
        self.out = self.root/'export'; self.out.mkdir(mode=0o700)
        self.archive = self.export()
        self.image = self.root/'normal.img'; self.image.write_bytes(b'explicit tiny fake reader input')
        self.manifest = dict(release='supported', state_schema=1, release_revision=4,
                             project_source_revision=REVISION, hardware_profile='fixture', klipper_commit='3'*40,
                             mcu_firmware=dict(format_version=1, release='supported', host_klipper_commit='3'*40, definitions=[]))
        self.artifact = dict(status='supported-candidate-awaiting-qualification', image_sha256=self.sha(self.image),
                             profile=dict(self.manifest, purpose='supported-configured-printer-candidate'))
        self.receipt = self.root/'composition.json'; self.write_receipt()
        self.serial = 0

    def tearDown(self): self.tmp.cleanup()
    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def write_receipt(self): self.receipt.write_text(json.dumps(self.artifact))
    def export(self):
        export = Export(self.data, {'local':dict(path=self.out)}, local_admission)
        return self.out/export.execute(export.prepare('local'))['filename']
    def call(self, **changes):
        self.serial += 1
        arguments = dict(archive=self.archive, archive_sha256=self.sha(self.archive), source=self.source,
                         image=self.image, image_sha256=self.sha(self.image), receipt=self.receipt,
                         receipt_sha256=self.sha(self.receipt), source_revision=REVISION,
                         workspace=self.root/('work'+str(self.serial)), reader=lambda *args: self.manifest)
        arguments.update(changes)
        return prepare(**arguments)
    def reject(self, **changes):
        with self.assertRaises((ValueError, sqlite3.DatabaseError, KeyError)): self.call(**changes)
        self.assertFalse((self.root/('work'+str(self.serial))/'installation.tar').exists())
        self.assertFalse((self.root/('work'+str(self.serial))/'receipt.json').exists())

    def test_preservation_wal_exact_seed_roundtrip_and_boot_reuse(self):
        original = self.archive.read_bytes(); registry = (self.store.root/'state.json').read_bytes()
        initial = contents(self.data)
        old_generations = contents(self.store.root/'generations')
        retained = retained_system(self.store.root)
        result = self.call(); work = Path(result['archive']).parent
        self.assertEqual(original, self.archive.read_bytes()); self.assertEqual(initial, contents(self.data))
        seed = work/'roundtrip/sv08'; store = Store(seed); state = compatible(seed, TARGET, False)
        record = state['slots']['A']; new = store.generation_path(record)
        self.assertEqual(record['parent_generation'], self.source['generation'])
        self.assertNotEqual(record['generation'], self.source['generation'])
        self.assertEqual([row for row in contents(seed/'generations') if row[0][0] != record['generation']],
                         old_generations)
        self.assertEqual(retained_system(seed), retained)
        self.assertEqual(state['slots']['B'], self.store.load()['slots']['B'])
        self.assertEqual(state['owner_policy_note'], 'preserve arbitrary policy records')
        backup = next(seed.glob('installation-preparation-*'))
        self.assertEqual((backup/'original-state.json').read_bytes(), registry)
        self.assertEqual((backup/'klipper-start.json').read_bytes(), b'exact old commissioning permission')
        self.assertFalse((seed/'system/klipper-start.json').exists())
        from sv08_commissioning import Commissioning
        commissioning = Commissioning(store, uid=os.geteuid())
        # Admit only the publication snapshot seam, without inventing OS health
        # or physical evidence. The normal permission reader/check is unchanged.
        with patch.object(commissioning, 'snapshot', return_value=dict(review=dict(permission={}))):
            with self.assertRaisesRegex(ValueError, 'separately reviewed commissioning permission'):
                commissioning.check()
        self.assertEqual((new/'config/printer.cfg').read_bytes(), b'user config and calibration\n')
        before = (self.generation/'config/printer.cfg').stat(); after = (new/'config/printer.cfg').stat()
        self.assertEqual((before.st_mode, before.st_uid, before.st_gid), (after.st_mode, after.st_uid, after.st_gid))
        self.assertEqual(os.readlink(seed/'system/identity/current'), 'generations/'+'b'*32)
        self.assertEqual(json.loads((new/'mcu-firmware.json').read_bytes()), self.manifest['mcu_firmware'])
        self.assertEqual(json.loads((seed/'generations'/self.source['generation']/'mcu-firmware.json').read_bytes()), self.old_assignment)
        with sqlite3.connect(new/'database/app.db') as db:
            self.assertEqual(db.execute('SELECT * FROM calibration').fetchall(), [(1, 'retained committed row')])
            self.assertIn('CREATE TABLE calibration', db.execute("SELECT sql FROM sqlite_master WHERE name='calibration'").fetchone()[0])
        with patch('sv08_printer_firmware.installed_assignment', return_value=self.manifest['mcu_firmware']):
            boot = store.prepare_boot('A', 'supported', 1, 4)
        self.assertEqual(Path(boot['generation']), new); self.assertFalse(boot['trial'])
        proof = json.loads((work/'receipt.json').read_text())
        self.assertEqual(proof['output_archive_sha256'], self.sha(Path(result['archive'])))
        self.assertTrue(proof['physical_start_quarantined'])
        self.assertNotIn(self.source['generation'], json.dumps(result))

    def test_input_and_source_binding_refusals(self):
        self.reject(archive_sha256='0'*64)
        self.reject(image_sha256='0'*64)
        self.reject(receipt_sha256='0'*64)
        for key, value in [('generation','wrong'),('release','wrong'),('release_revision',3),('state_schema',2),('slot','invalid')]:
            with self.subTest(key=key): self.reject(source=dict(self.source, **{key:value}))
        self.reject(source_revision='4'*40)
        self.manifest['mcu_firmware']['host_klipper_commit'] = '5'*40
        self.reject()
        self.manifest['mcu_firmware']['host_klipper_commit'] = '3'*40
        self.artifact['image_sha256'] = '0'*64; self.write_receipt(); self.reject()
        self.artifact['image_sha256'] = self.sha(self.image)
        self.artifact['profile']['release_revision'] = 7; self.write_receipt(); self.reject()

    def test_unsafe_state_and_budget_refusals(self):
        registry = self.store.load()
        for change in ('writable','customized','pending'):
            state = json.loads(json.dumps(registry))
            if change == 'writable': state['requested_mode'] = 'writable'
            elif change == 'customized': state['slots']['B']['customized'] = True
            else: state['pending'] = dict(slot='A', release='next', previous_slot='B', phase='armed', id='fixture')
            self.store.save(state); self.archive = self.export()
            with self.subTest(change=change): self.reject()
        self.store.save(registry); self.archive = self.export()
        with patch('sv08_state.Store.check_copy_budget', side_effect=ValueError('Insufficient state-copy budget')):
            self.reject()
        # Generation links are rejected by archive validation, before copying.
        (self.generation/'config/link').symlink_to('/outside')
        with self.assertRaises(ValueError): self.export()

    def test_completed_history_retained_interrupted_and_corruption_refuse(self):
        history = self.store.root/'customizations'; history.mkdir()
        completed = history/'done.json'; completed.write_text(json.dumps(dict(status='completed', exit_status=0)))
        activation = self.data/'.sv08-activation-fixture.json'
        activation.write_text(json.dumps(dict(format_version=1, phase='committed')))
        update = self.store.root/'update.json'
        transaction = dict(format_version=1, phase='complete', slot='A', previous_slot='B',
                           id='historical', release='supported', previous_release='legacy',
                           boot_id='fixture', bundle_sha256='a'*64)
        update.write_text(json.dumps(transaction))
        self.archive = self.export(); result = self.call()
        restored = Path(result['archive']).parent/'roundtrip'
        self.assertEqual((restored/'sv08/customizations/done.json').read_bytes(), completed.read_bytes())
        for path, value in [(completed, dict(status='started')),
                            (activation, dict(format_version=1, phase='saved')),
                            (activation, dict(format_version=1, phase='unknown')),
                            (update, dict(transaction, phase='installing'))]:
            raw = path.read_bytes(); path.write_text(json.dumps(value)); self.archive = self.export()
            self.reject(); path.write_bytes(raw)
        for suffix in ('-wal', '-shm'):
            (self.generation/('database/app.db'+suffix)).unlink()
        (self.generation/'database/app.db').write_bytes(b'SQLite format 3\0'+b'corrupt'*100)
        self.archive = self.export(); self.reject()

    def test_archive_mutation_during_reader_refuses_before_output(self):
        def change(*unused):
            self.archive.write_bytes(self.archive.read_bytes()+b'bad')
            return self.manifest
        self.reject(reader=change)

    def test_raw_same_release_restore_contract_is_unchanged(self):
        from prepare_recovery_installation_archive import Workspace, restore
        work = self.root/'raw'; work.mkdir(mode=0o700)
        restore(self.archive, work/'data', Workspace(work))
        compatible(work/'data/sv08', SOURCE, False)
        with self.assertRaisesRegex(ValueError, 'differs from reviewed'):
            compatible(work/'data/sv08', TARGET, False)
        with self.assertRaisesRegex(ValueError, 'Unannounced'):
            Store(work/'data/sv08').prepare_boot('A', 'supported', 1, 4)

    def test_actual_reader_binding_logic_with_explicit_fake_mount_helper(self):
        # This exercises selection/binding logic, not kernel mount verification.
        from contextlib import contextmanager
        root = self.root/'fake-mounted'; (root/'usr/lib/sv08').mkdir(parents=True)
        embedded = root/'usr/lib/sv08/release.json'
        embedded.write_text(json.dumps(self.manifest))
        part = dict(number=3, name='root-a', offset_bytes=0, size_bytes=self.image.stat().st_size)
        artifact = dict(image_bytes=self.image.stat().st_size,
                        geometry=dict(partition_records=[part]),
                        partition_images={'root-a':dict(bytes=part['size_bytes'], sha256=self.sha(self.image))})
        @contextmanager
        def fake_mount(image, selected, scratch):
            self.assertEqual(selected, part)
            yield root
        with patch('image_license_inventory.geometry', return_value=[part]), \
                patch('image_license_inventory.mounted_image', side_effect=fake_mount):
            self.assertEqual(image_manifest(self.image, self.root, artifact), self.manifest)
            artifact['partition_images']['root-a']['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'partition differs'):
                image_manifest(self.image, self.root, artifact)
            artifact['geometry']['partition_records'] = []
            with self.assertRaisesRegex(ValueError, 'geometry differs'):
                image_manifest(self.image, self.root, artifact)

    def test_actual_reader_has_no_manifest_only_fallback(self):
        # The unit input is deliberately not an image. Native binding is a later
        # coordinator check; this verifies actual CLI reader refuses fake bytes.
        with self.assertRaisesRegex(ValueError, 'Unsupported or truncated image'):
            image_manifest(self.image, self.root, self.artifact)


if __name__ == '__main__': unittest.main()
