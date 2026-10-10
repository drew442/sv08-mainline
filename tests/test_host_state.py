from test_data_budget import fixture_budget, fixture_root
import json
import os
from types import SimpleNamespace
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_state import Store, fingerprint


class PersistentStateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=fixture_root())
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / 'data', reserve_bytes=0, budget=fixture_budget())
        self.store.initialize()
        self.a = self.store.prepare_boot('A', 'release-1')
        self.config = Path(self.a['generation']) / 'config/printer.cfg'
        self.config.write_text('before staging')

    def test_default_mode_and_both_switch_directions_preserve_customization(self):
        self.assertEqual(self.a['mode'], 'immutable')
        self.store.policy(mode='writable')
        b = self.store.prepare_boot('A', 'release-1')
        self.assertEqual(b['generation'], self.a['generation'])
        self.assertTrue(b['customized'])
        self.store.policy(mode='immutable')
        c = self.store.prepare_boot('A', 'release-1')
        self.assertTrue(c['customized'])
        self.assertEqual(self.config.read_text(), 'before staging')
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            self.store.expect_trial('B', 'release-2', 'A')

    def test_delayed_boot_copies_latest_state_and_rollback_preserves_generations(self):
        self.store.expect_trial('B', 'release-2', 'A')
        self.config.write_text('edited after staging')
        b = self.store.prepare_boot('B', 'release-2')
        newer = Path(b['generation']) / 'config/printer.cfg'
        self.assertEqual(newer.read_text(), 'edited after staging')
        newer.write_text('B-only change')
        a = self.store.prepare_boot('A', 'release-1')
        self.assertEqual(a['generation'], self.a['generation'])
        self.assertEqual(self.config.read_text(), 'edited after staging')
        self.assertEqual(newer.read_text(), 'B-only change')
        self.assertIsNone(self.store.load()['pending'])
        self.assertEqual(self.store.load()['last_failed_trial']['release'], 'release-2')

    def test_committed_sqlite_wal_is_included(self):
        database = Path(self.a['generation']) / 'database/test.db'
        with sqlite3.connect(database) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE settings(value TEXT)')
            db.commit()
            self.store.expect_trial('B', 'release-2', 'A')
            db.execute("INSERT INTO settings VALUES ('late committed value')")
            db.commit()
            before = fingerprint(Path(self.a['generation']))
            b = self.store.prepare_boot('B', 'release-2')
            self.assertEqual(fingerprint(Path(self.a['generation'])), before)
            with sqlite3.connect(Path(b['generation']) / 'database/test.db') as copied:
                self.assertEqual(copied.execute('SELECT value FROM settings').fetchall(), [('late committed value',)])

    def test_mode_change_and_transaction_conflict(self):
        self.store.expect_trial('B', 'release-2', 'A')
        with self.assertRaisesRegex(ValueError, 'pending'):
            self.store.policy(mode='writable')
        self.store.policy(auto_update=False)
        self.assertFalse(self.store.load()['auto_update'])
        self.store.cancel_trial()
        self.assertIsNone(self.store.load()['pending'])
        self.store.policy(mode='writable')

    def test_closed_wal_database_snapshot_leaves_source_files_unchanged(self):
        database = Path(self.a['generation']) / 'database/test.db'
        db = sqlite3.connect(database)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE settings(value TEXT)')
        db.execute("INSERT INTO settings VALUES ('checkpointed value')")
        db.commit()
        db.close()
        self.assertFalse(Path(str(database) + '-wal').exists())
        before = fingerprint(Path(self.a['generation']))
        self.store.expect_trial('B', 'release-2', 'A')
        b = self.store.prepare_boot('B', 'release-2')
        self.assertEqual(fingerprint(Path(self.a['generation'])), before)
        self.assertFalse(Path(str(database) + '-wal').exists())
        copied = sqlite3.connect(Path(b['generation']) / 'database/test.db')
        try:
            self.assertEqual(copied.execute('SELECT value FROM settings').fetchall(), [('checkpointed value',)])
            self.assertEqual(copied.execute('PRAGMA quick_check').fetchone(), ('ok',))
        finally:
            copied.close()

    def test_sqlite_backup_workspace_is_reserved_before_copy(self):
        database = Path(self.a['generation']) / 'database/test.db'
        db = sqlite3.connect(database)
        db.execute('CREATE TABLE settings(value TEXT)')
        db.commit()
        db.close()
        record = self.store.load()['slots']['A']
        block = os.statvfs(self.store.root).f_frsize
        ordinary_copy = block + sum(block if p.is_dir() else ((p.stat().st_size + block - 1) // block) * block
                                    for p in Path(self.a['generation']).rglob('*'))
        report = self.store.check_copy_budget(record)
        self.assertGreaterEqual(report['copy_bytes'], ordinary_copy + database.stat().st_size + 4 * block)
        self.store.copy_limit_bytes = ordinary_copy
        self.store.expect_trial('B', 'release-2', 'A')
        before = self.store.load()
        with self.assertRaisesRegex(ValueError, 'budget'):
            self.store.prepare_boot('B', 'release-2')
        self.assertEqual(self.store.load(), before)

    def test_snapshot_still_rejects_real_source_changes(self):
        import shutil
        copytree = shutil.copytree
        self.store.expect_trial('B', 'release-2', 'A')
        before = self.store.load()
        def changed(source, target, *args, **kwargs):
            result = copytree(source, target, *args, **kwargs)
            if Path(source) == Path(self.a['generation']):
                self.config.write_text('external writer changed source')
            return result
        with patch('sv08_state.shutil.copytree', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'State changed during copy'):
                self.store.prepare_boot('B', 'release-2')
        self.assertEqual(self.store.load(), before)

    def test_private_sqlite_peak_fits_copy_admission_without_shm(self):
        from sv08_state import snapshot
        source = Path(self.a['generation'])
        database = source / 'database/test.db'
        db = sqlite3.connect(database)
        self.addCleanup(db.close)
        db.execute('PRAGMA page_size=512')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA wal_autocheckpoint=0')
        db.execute('CREATE TABLE values_seen(value BLOB)')
        db.executemany('INSERT INTO values_seen VALUES (?)', [(bytes(400),)] * 4500)
        db.commit()
        target = self.store.root / 'generations/private-copy-probe'
        budget = self.store.check_copy_budget(self.store.load()['slots']['A'])['copy_bytes']
        peaks = []
        def observe():
            files = list(target.rglob('*'))
            self.assertFalse(any(p.name.endswith('-shm') for p in files))
            peaks.append(target.stat().st_blocks * 512 + sum(p.stat().st_blocks * 512 for p in files))
        class ObservedConnection(sqlite3.Connection):
            def execute(connection, *args, **kwargs):
                result = super().execute(*args, **kwargs)
                observe()
                return result
            def backup(connection, other, *args, **kwargs):
                result = super().backup(other, *args, **kwargs)
                observe()
                return result
        connect = sqlite3.connect
        before = fingerprint(source)
        with patch('sv08_state.sqlite3.connect', side_effect=lambda *args, **kwargs: connect(*args, factory=ObservedConnection, **kwargs)):
            snapshot(source, target)
        self.assertEqual(fingerprint(source), before)
        self.assertTrue(peaks)
        self.assertLessEqual(max(peaks), budget)

    def test_policy_rejects_non_boolean_without_publishing_other_changes(self):
        before = self.store.load()
        for value in ('false', 'true', 0, 1, [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                self.store.policy(mode='writable', auto_update=value)
            self.assertEqual(self.store.load(), before)

    def test_copy_failure_never_publishes_b(self):
        self.store.expect_trial('B', 'release-2', 'A')
        with patch('sv08_state.snapshot', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.store.prepare_boot('B', 'release-2')
        self.assertNotIn('B', self.store.load()['slots'])
        self.assertEqual(self.config.read_text(), 'before staging')

    def test_full_disk_and_unsupported_schema_preserve_original(self):
        self.store.expect_trial('B', 'release-2', 'A')
        self.store.copy_limit_bytes = 1
        with self.assertRaisesRegex(ValueError, 'budget'):
            self.store.prepare_boot('B', 'release-2')
        with self.assertRaisesRegex(ValueError, 'schema'):
            self.store.prepare_boot('B', 'release-2', 2)
        self.assertNotIn('B', self.store.load()['slots'])

    def test_symlink_config_cannot_escape_state_copy(self):
        self.config.unlink()
        self.config.symlink_to('/etc/passwd')
        self.store.expect_trial('B', 'release-2', 'A')
        with self.assertRaisesRegex(ValueError, 'regular files'):
            self.store.prepare_boot('B', 'release-2')
        self.assertNotIn('B', self.store.load()['slots'])

    def test_corrupt_policy_not_silently_reset(self):
        state = self.store.root / 'state.json'
        state.write_text('{interrupted/corrupt data')
        with self.assertRaises(json.JSONDecodeError):
            self.store.initialize()
        self.assertEqual(state.read_text(), '{interrupted/corrupt data')

    def test_trial_reboot_reuses_generation(self):
        self.store.expect_trial('B', 'release-2', 'A')
        b = self.store.prepare_boot('B', 'release-2')
        again = self.store.prepare_boot('B', 'release-2')
        self.assertEqual(b['generation'], again['generation'])
        self.store.confirm('B', 'release-2')
        self.assertFalse(self.store.prepare_boot('B', 'release-2')['trial'])

    def test_corrupt_pending_transaction_fails_closed(self):
        self.store.expect_trial('B', 'release-2', 'A')
        state = self.store.load()
        state['pending']['previous_slot'] = 'B'
        self.store.save(state)
        with self.assertRaisesRegex(ValueError, 'pending transaction'):
            self.store.prepare_boot('B', 'release-2')

    def test_copy_budget_counts_blocks_and_sparse_expansion(self):
        record = self.store.load()['slots']['A']
        block = os.statvfs(self.store.root).f_frsize
        with self.config.open('wb') as stream:
            stream.truncate(block * 20 + 1)
        report = self.store.check_copy_budget(record)
        self.assertGreaterEqual(report['copy_bytes'], block * 25)
        self.store.copy_limit_bytes = block * 20
        with self.assertRaisesRegex(ValueError, 'budget'):
            self.store.check_copy_budget(record)

    def test_space_and_inode_exhaustion_preserve_trial_source(self):
        self.store.expect_trial('B', 'release-2', 'A')
        for values in (dict(f_bavail=0, f_favail=10000),
                       dict(f_bavail=1000000, f_favail=1)):
            fs = SimpleNamespace(f_frsize=4096, f_bsize=4096, **values)
            with self.subTest(values=values), patch('sv08_state.os.statvfs', return_value=fs):
                with self.assertRaisesRegex(ValueError, 'space or inodes'):
                    self.store.prepare_boot('B', 'release-2')
            self.assertNotIn('B', self.store.load()['slots'])
            self.assertEqual(self.config.read_text(), 'before staging')

    def test_staging_reserves_full_late_copy_allowance(self):
        record = self.store.load()['slots']['A']
        fs = SimpleNamespace(f_frsize=4096, f_bsize=4096, f_bavail=3000, f_favail=10000)
        with patch('sv08_state.os.statvfs', return_value=fs):
            self.store.check_copy_budget(record)
            with self.assertRaisesRegex(ValueError, 'space or inodes'):
                self.store.check_copy_budget(record, reserve_full_copy=True)
