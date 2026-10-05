"""Read-only inventory tests; do not assert that a pending task is authorized."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workflow_inventory import LIMIT, load_records, main, summarize


def record(version=1, state='pending', environment='offline'):
    task = {'id': 'build', 'status': state, 'environment': environment,
            'depends_on': [], 'blocker': 'Owner deferred; do not resume' if state == 'blocked' else None}
    if version == 2:
        task['review_policy'] = 'self'
    return {'id': 'example', 'format_version': version, 'tasks': [task]}


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root / 'docs/features/example'
        self.folder.mkdir(parents=True)

    def write(self, value):
        path = self.folder / 'record.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def row(self, value):
        return summarize({'example': value})['tasks'][0]

    def test_pending_legacy_needs_assessment_not_automatic_migration(self):
        row = self.row(record())
        self.assertEqual(row['inspection_action'], 'assess_remaining_scope_for_v2')
        self.assertEqual(row['review_policy'], 'legacy')
        self.assertNotIn('ready', row)

    def test_done_retains_history_without_testing_its_old_evidence(self):
        self.assertEqual(self.row(record(state='done'))['inspection_action'], 'preserve_history')

    def test_blocked_prose_is_not_interpreted_as_permission_or_cancellation(self):
        r = record(state='blocked')
        r['tasks'][0]['blocker'] = 'Fix ready; pending; abandoned; review passed; resume now'
        row = self.row(r)
        self.assertEqual(row['recorded_status'], 'blocked')
        self.assertEqual(row['inspection_action'], 'respect_existing_blocker')
        self.assertEqual(row['blocker'], r['tasks'][0]['blocker'])

    def test_frozen_and_running_candidates_need_live_reconciliation(self):
        for state in ('running', 'review', 'validated'):
            with self.subTest(state=state):
                self.assertEqual(self.row(record(2, state))['inspection_action'],
                                 'reconcile_active_assignment')

    def test_physical_pending_work_never_becomes_a_migration_recommendation(self):
        for environment in ('hardware', 'human'):
            self.assertEqual(self.row(record(environment=environment))['inspection_action'],
                             'manual_hardware_or_human_queue')

    def test_v2_routes_are_preserved_not_downgraded(self):
        for route in ('self', 'targeted', 'consequential'):
            r = record(2); r['tasks'][0]['review_policy'] = route
            self.assertEqual(self.row(r)['review_policy'], route)

    def test_dependencies_and_reverse_references_are_reported(self):
        a, b = record(), record(2)
        b['id'] = 'second'; b['tasks'][0]['depends_on'] = ['example:build', 'missing:task']
        rows = summarize({'example': a, 'second': b})['tasks']
        self.assertEqual(rows[0]['referenced_by'], ['second:build'])
        self.assertEqual(rows[1]['dependencies'][1]['recorded_status'], 'missing')
        self.assertEqual(rows[1]['inspection_action'], 'use_v2_after_workflow_checks')

    def test_missing_route_or_unsupported_version_cannot_become_self(self):
        for version in (True, 0, 3, '2', None):
            r = record(); r['format_version'] = version
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                self.row(r)
        r = record(2); del r['tasks'][0]['review_policy']
        with self.assertRaisesRegex(ValueError, 'Unknown review'):
            self.row(r)

    def test_invalid_inventory_fields_are_rejected(self):
        for key, value in (('status', 'cancelled'), ('environment', 'production'),
                           ('depends_on', 'example:build'), ('id', '')):
            r = record(); r['tasks'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.row(r)
        r = record(); r['tasks'].append(deepcopy(r['tasks'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate task'):
            self.row(r)

    def test_input_objects_are_not_modified(self):
        records = {'example': record(state='blocked')}; before = deepcopy(records)
        summarize(records)
        self.assertEqual(records, before)

    def test_cli_records_exact_hashes_and_leaves_bytes_unchanged(self):
        path = self.write(record()); before = path.read_bytes()
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(main(['--repo', str(self.root)]), 0)
        report = json.loads(stream.getvalue())
        self.assertTrue(report['inventory_only'])
        self.assertEqual(len(report['tasks'][0]['record_sha256']), 64)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / 'local').exists())
        self.assertIsNone(report['checkout_head'])

    def test_duplicate_json_and_oversize_input_are_rejected(self):
        path = self.folder / 'record.json'
        path.write_text('{"id":"example","id":"other"}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            load_records(self.root)
        path.write_bytes(b' ' * (LIMIT + 1))
        with self.assertRaisesRegex(ValueError, 'Oversize'):
            load_records(self.root)

    def test_mismatched_id_and_nonfinite_json_are_rejected(self):
        self.write({'id': 'other'})
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            load_records(self.root)
        (self.folder / 'record.json').write_text('{"id":"example","x":NaN}')
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            load_records(self.root)

    def test_symlink_records_and_directories_are_not_followed(self):
        target = self.root / 'private.json'; target.write_text('{"id":"example"}')
        path = self.folder / 'record.json'; path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            load_records(self.root)
        path.unlink(); self.folder.rmdir(); self.folder.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            load_records(self.root)

    def test_empty_inventory_is_distinct_from_missing_tree(self):
        report = summarize({})
        self.assertEqual(report['task_count'], 0)
        self.assertTrue(report['inventory_only'])
        with self.assertRaisesRegex(ValueError, 'Missing'):
            load_records(self.root / 'not-a-checkout')

    def test_cli_has_no_mutating_option(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            main(['--repo', str(self.root), '--execute'])
        self.assertEqual(exc.exception.code, 2)

    def test_cli_failure_does_not_emit_success_report(self):
        self.write({'id': 'example', 'format_version': 99})
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--repo', str(self.root)]), 2)
        self.assertEqual(output.getvalue(), '')

    def test_actual_subprocess_cli_without_history_is_read_only(self):
        path = self.write(record())
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] /
                                 'scripts/workflow_inventory.py'), '--repo', str(self.root)],
                                text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)['task_count'], 1)
        self.assertEqual(json.loads(path.read_text()), record())


if __name__ == '__main__':
    unittest.main()
