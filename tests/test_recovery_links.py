"""Opaque provisioned links are data, never extraction or mutation paths."""
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from sv08_export import Export, inventory
from sv08_restore import Restore
from test_restore import admission
from test_data_budget import fixture_root
import test_recovery_activation


def provision(root):
    identity = root/'sv08/system/identity'
    for token in ('a'*32, 'b'*32):
        generation = identity/'generations'/token
        generation.mkdir(parents=True)
        (generation/'opaque').write_bytes(b'synthetic identity')
    for name, token in (('current', 'a'*32), ('previous', 'b'*32)):
        (identity/name).symlink_to('generations/'+token)
        os.utime(identity/name, (1700000000, 1700000000), follow_symlinks=False)
    logs = root/'sv08/shared/logs'; logs.mkdir(parents=True)
    (logs/'README').symlink_to('../../usr/share/doc/systemd/README.logs')
    (root/'sv08/state.json').write_bytes(b'damaged registry preserved')
    return identity


class RecoveryLinksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root/'source'; self.source.mkdir()
        self.identity = provision(self.source)
        self.usb = self.root/'usb'; self.usb.mkdir()
        self.parent = self.root/'target'; self.parent.mkdir()
        self.exporter = Export(self.source, {'usb':dict(path=self.usb)}, admission, reserve_bytes=0)
    def export(self):
        result = self.exporter.execute(self.exporter.prepare('usb'))
        return self.usb/result['filename']
    def restorer(self, archive):
        return Restore({'backup':dict(path=archive)}, {'target':dict(root=self.parent/'restored')}, admission, reserve_bytes=0)
    def rewrite(self, archive, change):
        with tarfile.open(archive) as reader:
            entries = [(item, reader.extractfile(item).read() if item.isfile() else None) for item in reader]
        change(entries)
        with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as writer:
            for item, data in entries: writer.addfile(item, io.BytesIO(data) if data is not None else None)
    def test_provisioned_roundtrip_links_metadata_and_private_bytes(self):
        archive = self.export(); before = archive.read_bytes()
        with tarfile.open(archive) as reader:
            manifest = json.load(reader.extractfile('export-manifest.json'))
            self.assertEqual(manifest['format_version'], 2)
            self.assertEqual(manifest['nodes']['data/sv08/system/identity/current']['target'], 'generations/'+'a'*32)
        restore = self.restorer(archive); restore.execute(restore.prepare('target', 'backup'))
        for path in self.source.rglob('*'):
            other = self.parent/'restored'/path.relative_to(self.source)
            a, b = path.lstat(), other.lstat()
            self.assertEqual((stat.S_IMODE(a.st_mode), a.st_uid, a.st_gid, int(a.st_mtime)),
                             (stat.S_IMODE(b.st_mode), b.st_uid, b.st_gid, int(b.st_mtime)))
            if path.is_symlink(): self.assertEqual(os.readlink(path), os.readlink(other))
            elif path.is_file(): self.assertEqual(path.read_bytes(), other.read_bytes())
        self.assertEqual(before, archive.read_bytes())
        self.assertEqual(stat.S_IMODE((self.parent/'restored').stat().st_mode), 0o700)
    def test_retained_and_arbitrary_state_anchors_with_damaged_registry_roundtrip(self):
        import shutil
        retained = self.source/('.sv08-previous-'+'c'*32)
        shutil.copytree(self.source/'sv08', retained, symlinks=True)
        configured = self.source/'configured-fresh-root'
        shutil.copytree(self.source/'sv08', configured, symlinks=True)
        nested = self.source/'custom-restore'/'sv08'; nested.parent.mkdir()
        shutil.copytree(self.source/'sv08', nested, symlinks=True)
        archive = self.export(); restore = self.restorer(archive)
        restore.execute(restore.prepare('target', 'backup'))
        for anchor in ('sv08', retained.name, configured.name, 'custom-restore/sv08'):
            state = self.parent/'restored'/anchor
            self.assertEqual(os.readlink(state/'system/identity/current'), 'generations/'+'a'*32)
            self.assertEqual((state/'state.json').read_bytes(), b'damaged registry preserved')
    def test_export_state_root_itself_and_entry_bound(self):
        self.exporter.source = self.source/'sv08'
        archive = self.export(); restore = self.restorer(archive)
        restore.execute(restore.prepare('target', 'backup'))
        self.assertEqual(os.readlink(self.parent/'restored/system/identity/current'), 'generations/'+'a'*32)
        from sv08_restore import pinned_archive, scan
        with pinned_archive(archive) as (fd, _):
            count = scan(fd)['entries']
            self.assertEqual(scan(fd, max_entries=count)['entries'], count)
            with self.assertRaisesRegex(ValueError, 'too many'): scan(fd, max_entries=count-1)
    def test_missing_or_link_backed_state_registry_refused(self):
        registry = self.source/'sv08/state.json'; registry.unlink()
        with self.assertRaises(ValueError): self.exporter.prepare('usb')
        registry.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError): self.exporter.prepare('usb')
    def test_manifest_bound_refuses_without_publication(self):
        with patch('sv08_export.MAX_MANIFEST', 100):
            with self.assertRaisesRegex(ValueError, 'metadata bound'):
                self.exporter.execute(self.exporter.prepare('usb'))
        self.assertEqual(list(self.usb.iterdir()), [])
    def test_wrong_escape_absolute_dangling_and_cycle_selectors_refused(self):
        selector = self.identity/'current'
        for target in ('/etc/passwd', '../generations/'+'a'*32, 'generations/'+'c'*32, 'previous', 'generations/not-a-token'):
            with self.subTest(target=target):
                selector.unlink(); selector.symlink_to(target)
                with self.assertRaises(ValueError): self.exporter.prepare('usb')
                self.assertEqual(list(self.usb.iterdir()), [])
    def test_generation_ancestor_link_and_nonstate_selector_refused(self):
        generation = self.identity/'generations'/('a'*32)
        generation.rename(self.root/'outside')
        generation.symlink_to(self.root/'outside')
        with self.assertRaises(ValueError): self.exporter.prepare('usb')
        generation.unlink(); (self.root/'outside').rename(generation)
        (self.source/'current').symlink_to('sv08/system/identity/generations/'+'a'*32)
        with self.assertRaises(ValueError): self.exporter.prepare('usb')
    def test_log_link_exact_leaf_only(self):
        link = self.source/'sv08/shared/logs/README'; link.unlink(); link.symlink_to('elsewhere')
        with self.assertRaises(ValueError): self.exporter.prepare('usb')
        link.unlink(); link.symlink_to('../../usr/share/doc/systemd/README.logs')
        (link.parent/'alias').symlink_to('../../usr/share/doc/systemd/README.logs')
        with self.assertRaises(ValueError): self.exporter.prepare('usb')
    def test_review_retarget_and_readlink_race_refuse_publication(self):
        plan = self.exporter.prepare('usb'); selector = self.identity/'current'
        selector.unlink(); selector.symlink_to('generations/'+'b'*32)
        with self.assertRaisesRegex(ValueError, 'changed'): self.exporter.execute(plan)
        original = os.readlink
        def race(name, **kwargs):
            target = original(name, **kwargs)
            if name == 'current':
                selector.unlink(); selector.symlink_to('generations/'+'a'*32)
            return target
        with patch('sv08_recovery_links.os.readlink', side_effect=race):
            with self.assertRaisesRegex(ValueError, 'changed'): inventory(self.source)
        self.assertEqual(list(self.usb.iterdir()), [])
    def test_unmanifested_target_and_node_metadata_tampering_refused(self):
        for defect in ('target', 'directory-mode', 'link-owner', 'link-mode'):
            archive = self.export()
            def change(entries):
                for item, _ in entries:
                    if defect == 'target' and item.issym(): item.linkname = 'generations/'+'b'*32; break
                    if defect == 'directory-mode' and item.isdir(): item.mode ^= 0o100; break
                    if defect == 'link-owner' and item.issym(): item.uid += 1; break
                    if defect == 'link-mode' and item.issym(): item.mode = 0o700; break
            self.rewrite(archive, change)
            with self.subTest(defect=defect), self.assertRaises(ValueError): self.restorer(archive).prepare('target', 'backup')
            self.assertFalse((self.parent/'restored').exists())
    def test_tar_link_ancestor_is_refused_before_following(self):
        archive = self.export()
        def change(entries):
            for item, _ in entries:
                if item.name == 'data/sv08/system/identity/generations':
                    item.type = tarfile.SYMTYPE; item.linkname = str(self.root/'outside'); break
        self.rewrite(archive, change)
        with self.assertRaises(ValueError): self.restorer(archive).prepare('target', 'backup')
        self.assertFalse((self.root/'outside').exists())
    def test_staged_link_retarget_is_never_published_or_followed(self):
        archive = self.export(); restore = self.restorer(archive)
        plan = restore.prepare('target', 'backup')
        outside = self.root/'outside'; outside.write_bytes(b'unchanged outside')
        before = outside.stat(); original = os.symlink
        def changed(target, name, **kwargs):
            return original(str(outside) if name == 'current' else target, name, **kwargs)
        with patch('sv08_restore.os.symlink', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'Staged recovery link changed'): restore.execute(plan)
        self.assertFalse((self.parent/'restored').exists())
        self.assertEqual(outside.read_bytes(), b'unchanged outside')
        self.assertEqual(outside.stat(), before)
    def test_manifest_agreeing_arbitrary_link_is_still_refused(self):
        archive = self.export()
        def change(entries):
            for item, _ in entries:
                if item.name == 'data/sv08/system/identity/current': item.linkname = '/etc/passwd'
            for n, (item, data) in enumerate(entries):
                if item.name == 'export-manifest.json':
                    manifest = json.loads(data)
                    manifest['nodes']['data/sv08/system/identity/current']['target'] = '/etc/passwd'
                    for record in manifest['files']:
                        if record['path'] == 'data/sv08/system/identity/current': record['symlink'] = '/etc/passwd'
                    data = json.dumps(manifest).encode(); item.size = len(data); entries[n] = (item, data)
        self.rewrite(archive, change)
        with self.assertRaisesRegex(ValueError, 'Unsupported recovery link'): self.restorer(archive).prepare('target', 'backup')
    def test_legacy_v1_regular_archive_readable_but_link_extension_refused(self):
        archive = self.export()
        def downgrade(entries):
            entries[:] = [(item, data) for item, data in entries if not item.issym()]
            for n, (item, data) in enumerate(entries):
                if item.name == 'export-manifest.json':
                    manifest = json.loads(data); manifest['format_version'] = 1; del manifest['nodes']
                    manifest['files'] = [r for r in manifest['files'] if 'symlink' not in r]
                    data = json.dumps(manifest).encode(); item.size = len(data); entries[n] = (item, data)
        self.rewrite(archive, downgrade)
        restore = self.restorer(archive); restore.execute(restore.prepare('target', 'backup'))
        self.assertEqual((self.parent/'restored/sv08/state.json').read_bytes(), b'damaged registry preserved')
        archive = self.export()
        def invalid_downgrade(entries):
            for n, (item, data) in enumerate(entries):
                if item.name == 'export-manifest.json':
                    manifest = json.loads(data); manifest['format_version'] = 1; del manifest['nodes']
                    data = json.dumps(manifest).encode(); item.size = len(data); entries[n] = (item, data)
        self.rewrite(archive, invalid_downgrade)
        with self.assertRaises(ValueError): self.restorer(archive).prepare('target', 'backup')
    @unittest.skipUnless(os.geteuid() == 0, 'root ownership preservation requires root fixture check')
    def test_root_preserves_distinct_link_and_generation_ownership(self):
        selector = self.identity/'current'; os.chown(selector, 1234, 1235, follow_symlinks=False)
        generation = self.identity/'generations'/('a'*32); os.chown(generation, 1236, 1237)
        archive = self.export(); restore = self.restorer(archive); restore.execute(restore.prepare('target', 'backup'))
        restored = self.parent/'restored/sv08/system/identity'
        self.assertEqual((restored/'current').lstat().st_uid, 1234)
        self.assertEqual((restored/'current').lstat().st_gid, 1235)
        self.assertEqual((restored/'generations'/('a'*32)).stat().st_uid, 1236)


class ProvisionedActivationTests(test_recovery_activation.ActivationTests):
    # Reuse transactional regression checks with actual selectors present.
    def setUp(self):
        super().setUp()
        for root in (self.parent, self.parent/'restored'):
            identity = root/'sv08/system/identity'
            (identity/'generations'/('a'*32)).mkdir(parents=True)
            (identity/'current').symlink_to('generations/'+'a'*32)
            (identity/'previous').symlink_to('generations/'+'a'*32)
    def test_candidate_systemd_readme_and_selectors_activate_and_rollback(self):
        target = '../../usr/share/doc/systemd/README.logs'
        (self.parent/'restored/sv08/shared/logs/README').symlink_to(target)
        self.activation.execute(self.activation.prepare('target'))
        self.assertEqual(os.readlink(self.parent/'sv08/system/identity/current'), 'generations/'+'a'*32)
        self.assertEqual(os.readlink(self.parent/'sv08/shared/logs/README'), target)
        self.activation.execute(self.activation.prepare('target', rollback=True))
        self.assertEqual(self.configuration(), 'previous')
    def test_candidate_identity_selector_race_and_missing_generation_refuse(self):
        link = self.parent/'restored/sv08/system/identity/current'
        plan = self.activation.prepare('target'); link.unlink(); link.symlink_to('generations/'+'b'*32)
        with self.assertRaises((OSError, ValueError)): self.activation.execute(plan)
        self.assertEqual(self.configuration(), 'previous')
