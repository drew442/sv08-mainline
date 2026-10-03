"""Finite committed receipt snapshots. jobs.json is the sole commit point."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid
from sv08_data_budget import Budget, rounded, BATCH_BYTES, METADATA_BYTES

KIND = 'history-maintenance-v2'
ARCHIVES = 8
TOTAL = 1152
ALLOCATED = 64 * 1024 * 1024
ENTRIES = 64
MANIFEST_BYTES = 65536
HEX = r'[0-9a-f]{64}'
OBJECT = r'snapshot-([0-9a-f]{64})\.json'
TEMP = r'\.history-(?:object|manifest)-[0-9a-f]{32}'


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode()


def digest(value): return hashlib.sha256(encode(value)).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('Duplicate history JSON key')
            result[key] = value
        return result
    def constant(value): raise ValueError('Nonfinite history JSON number')
    try: return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError('Corrupt image history JSON') from error


@contextmanager
def directory(root):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(root).absolute().parts[1:]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            info = os.fstat(new)
            if info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o022:
                os.close(new); raise ValueError('Unsafe history ancestry')
            os.close(fd); fd = new
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('History directory must be private and owned')
        yield fd
    finally: os.close(fd)


def safe(info, links=1):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
            stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != links):
        raise ValueError('Unsafe image history file')


def pair(fd, held=None, required=False):
    names = os.listdir(fd)
    if 'history-format-v2.lock' not in names:
        if required: raise ValueError('Missing history compatibility fence')
        if 'ledger.lock' in names: safe(os.stat('ledger.lock', dir_fd=fd, follow_symlinks=False))
        return False
    a = os.stat('ledger.lock', dir_fd=fd, follow_symlinks=False)
    b = os.stat('history-format-v2.lock', dir_fd=fd, follow_symlinks=False)
    safe(a, 2); safe(b, 2)
    if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino): raise ValueError('Substituted history fence')
    if held is not None:
        h = os.fstat(held); safe(h, 2)
        if (h.st_dev, h.st_ino) != (a.st_dev, a.st_ino): raise ValueError('History lock inode changed')
    return True


def read(fd, name, limit):
    file = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        before = os.fstat(file); safe(before)
        if before.st_size > limit: raise ValueError('History object exceeds bound')
        with os.fdopen(os.dup(file), 'rb') as stream: raw = stream.read(limit+1)
        after = os.fstat(file)
        def stamp(info):
            return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
                    info.st_ctime_ns, info.st_uid, info.st_gid, info.st_nlink)
        bound = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stamp(before) != stamp(after) or stamp(after) != stamp(bound) or len(raw) != before.st_size:
            raise ValueError('History changed during read')
        return raw
    finally: os.close(file)


def validate_plan(plan):
    if (not isinstance(plan, dict) or set(plan) != {'kind', 'operation', 'revision', 'ids'} or
            plan['kind'] != KIND or plan['operation'] not in ('migrate', 'rollover') or
            not isinstance(plan['revision'], str) or not re.fullmatch(HEX, plan['revision']) or
            not isinstance(plan['ids'], list) or len(plan['ids']) > 128 or
            len(set(item for item in plan['ids'] if isinstance(item, str))) != len(plan['ids']) or
            any(not isinstance(item, str) or not re.fullmatch('[0-9a-f]{32}', item) for item in plan['ids'])):
        raise ValueError('Review image history maintenance first')


class History:
    def __init__(self, jobs):
        self.jobs, self.root = jobs, jobs.root
        self.budget = getattr(jobs, 'budget', None) or Budget(self.root.parent)
        self.fault = getattr(jobs, 'history_fault', lambda point: None)

    def namespace(self, fd):
        names = os.listdir(fd)
        objects, metadata, allocation = 0, 0, os.fstat(fd).st_blocks*512
        for name in names:
            entry = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if name in ('ledger.lock', 'history-format-v2.lock'):
                safe(entry, 2 if 'history-format-v2.lock' in names else 1)
            else: safe(entry)
            if (re.fullmatch(OBJECT, name) or re.fullmatch(r'\.history-object-[0-9a-f]{32}', name) or
                    name == 'jobs.json' and isinstance(strict_json(read(fd, name, BATCH_BYTES)), list) or
                    re.fullmatch(r'\.history-manifest-[0-9a-f]{32}', name) and entry.st_size > MANIFEST_BYTES):
                objects += 1
                if entry.st_size > BATCH_BYTES: raise ValueError('Oversized history debris')
            elif name not in ('jobs.json', 'worker.lock', 'ledger.lock', 'history-format-v2.lock') and not re.fullmatch(TEMP, name):
                raise ValueError('Unexpected history namespace entry')
            else: metadata += entry.st_blocks*512
            allocation += entry.st_blocks*512
        metadata += os.fstat(fd).st_blocks*512
        allocation_lock = self.budget.root / 'allocation.lock'
        extra = 0
        if allocation_lock.exists() or allocation_lock.is_symlink():
            info = allocation_lock.lstat(); safe(info)
            metadata += info.st_blocks*512; allocation += info.st_blocks*512; extra = 1
        if len(names)+1+extra > ENTRIES or objects > 16 or metadata > METADATA_BYTES or allocation > ALLOCATED:
            raise ValueError('History storage envelope exceeded')
        return dict(entries=len(names)+1+extra, objects=objects, metadata=metadata, allocated=allocation)

    def view(self):
        if not self.root.exists():
            if self.root.is_symlink(): raise ValueError('Invalid history directory')
            return self.legacy([])
        with directory(self.root) as fd:
            stats = self.namespace(fd); fenced = pair(fd)
            names = os.listdir(fd)
            if 'jobs.json' not in names:
                if fenced or any(re.fullmatch(OBJECT, n) or re.fullmatch(TEMP, n) for n in names):
                    raise ValueError('Missing committed image history; use recovery')
                return self.legacy([])
            raw = read(fd, 'jobs.json', BATCH_BYTES)
            value = strict_json(raw)
            if isinstance(value, list):
                self.jobs.validate_rows(value)
                view = self.legacy(value); view.update(fenced=fenced, stats=stats)
                return view
            if (not isinstance(value, dict) or set(value) != {'format_version', 'generation', 'parent_revision', 'active', 'archives', 'maintenance'} or
                    type(value['format_version']) is not int or value['format_version'] != 2 or
                    type(value['generation']) is not int or not 1 <= value['generation'] < 2**63 or
                    (value['parent_revision'] is not None if value['generation'] == 1 else
                     not isinstance(value['parent_revision'], str) or not re.fullmatch(HEX, value['parent_revision'])) or
                    not isinstance(value['archives'], list) or len(value['archives']) > ARCHIVES or len(raw) > MANIFEST_BYTES):
                raise ValueError('Unsupported or corrupt image history manifest')
            pair(fd, required=True)
            token = value['maintenance']
            if token is not None:
                if not isinstance(token, dict) or set(token) != {'plan', 'archive_sha256'}: raise ValueError('Invalid maintenance token')
                validate_plan(token['plan'])
                if not isinstance(token['archive_sha256'], str) or not re.fullmatch(HEX, token['archive_sha256']): raise ValueError('Invalid maintenance hash')
            rows, active, referenced = [], [], set()
            for index, desc in enumerate([*value['archives'], value['active']]):
                if (not isinstance(desc, dict) or set(desc) != {'name', 'sha256', 'bytes', 'count'} or
                        not isinstance(desc['sha256'], str) or not re.fullmatch(HEX, desc['sha256']) or
                        desc['name'] != 'snapshot-'+desc['sha256']+'.json' or
                        type(desc['bytes']) is not int or not 1 <= desc['bytes'] <= BATCH_BYTES or
                        type(desc['count']) is not int or not 0 <= desc['count'] <= 128):
                    raise ValueError('Invalid history snapshot descriptor')
                content = read(fd, desc['name'], BATCH_BYTES)
                if len(content) != desc['bytes'] or hashlib.sha256(content).hexdigest() != desc['sha256']:
                    raise ValueError('Corrupt history snapshot')
                batch = strict_json(content); self.jobs.validate_rows(batch)
                if len(batch) != desc['count']: raise ValueError('History snapshot count mismatch')
                if index < len(value['archives']):
                    if len(batch) != 128 or any(self.jobs.blocking(row) for row in batch): raise ValueError('Unsettled archive')
                else: active = batch
                rows.extend(batch); referenced.add(desc['name'])
            if len(rows) > TOTAL or len({row['id'] for row in rows}) != len(rows): raise ValueError('Duplicate or excessive retained identities')
            if token is not None:
                if not set(token['plan']['ids']).issubset({row['id'] for row in rows}): raise ValueError('Maintenance identities missing from committed history')
                if token['plan']['operation'] == 'rollover' and not any(desc['sha256'] == token['archive_sha256'] for desc in value['archives']):
                    raise ValueError('Maintenance archive is not committed')
            return dict(format=2, manifest=value, revision=digest(value), active=active, rows=rows,
                        referenced=referenced, fenced=True, stats=stats)

    @staticmethod
    def legacy(rows):
        return dict(format=1, manifest=None, revision=digest(rows), active=rows, rows=rows,
                    referenced=set(), fenced=False, stats={})

    def review(self, view=None):
        view = view or self.view()
        if any(self.jobs.blocking(row) for row in view['active']): raise ValueError('Unresolved image work blocks history maintenance')
        operation = 'migrate' if view['format'] == 1 else 'rollover'
        if operation == 'rollover' and len(view['manifest']['archives']) >= ARCHIVES:
            raise ValueError('Finite history archive ceiling reached; retained retries remain available, no eviction is offered')
        if operation == 'rollover' and len(view['active']) != 128:
            raise ValueError('History maintenance needs a complete settled batch of 128 receipts')
        block = os.statvfs(self.root).f_frsize or os.statvfs(self.root).f_bsize
        candidate = encode(view['active'] if operation == 'migrate' else [])
        delta = rounded(len(candidate), block)+rounded(MANIFEST_BYTES, block)+4*block
        if operation == 'migrate': delta += rounded(len(encode(view['active'])), block)
        self.budget.check(delta, 6)
        return dict(kind=KIND, operation=operation, revision=view['revision'], ids=[r['id'] for r in view['active']])

    def sync(self, fd, point):
        self.fault(point); os.fsync(fd)

    def settle(self, fd, view):
        for name in [*view['referenced'], *(['jobs.json'] if 'jobs.json' in os.listdir(fd) else [])]:
            file = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try: self.sync(file, 'recovery-file-fsync')
            finally: os.close(file)
        self.sync(fd, 'recovery-directory-fsync')
        with directory(self.root) as check:
            if (os.fstat(check).st_dev, os.fstat(check).st_ino) != (os.fstat(fd).st_dev, os.fstat(fd).st_ino): raise ValueError('History directory changed')
        self.parent_sync('recovery-parent-fsync')
        for name in os.listdir(fd):
            if (re.fullmatch(OBJECT, name) and name not in view['referenced']) or re.fullmatch(TEMP, name):
                safe(os.stat(name, dir_fd=fd, follow_symlinks=False))
                self.fault('cleanup'); os.unlink(name, dir_fd=fd)
        self.sync(fd, 'cleanup-directory-fsync')

    def parent_sync(self, point):
        file = os.open(self.root.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: self.sync(file, point)
        finally: os.close(file)

    def temporary(self, fd, kind, raw):
        name = '.history-'+kind+'-'+uuid.uuid4().hex
        self.fault(kind+'-create')
        file = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(file, 'wb') as output:
            self.fault(kind+'-write'); output.write(raw)
            self.fault(kind+'-flush'); output.flush()
            self.sync(output.fileno(), kind+'-file-fsync')
        return name

    def object(self, fd, raw, count):
        sha = hashlib.sha256(raw).hexdigest(); name = 'snapshot-'+sha+'.json'
        if name in os.listdir(fd):
            if read(fd, name, BATCH_BYTES) != raw: raise ValueError('Existing immutable history object differs')
        else:
            temporary = self.temporary(fd, 'object', raw)
            from sv08_export import publish
            self.fault('object-publish'); publish(fd, temporary, name)
        self.sync(fd, 'object-directory-fsync')
        return dict(name=name, sha256=sha, bytes=len(raw), count=count)

    def publish(self, view, rows, plan=None, result=False):
        self.jobs.validate_rows(rows)
        raw = encode(rows)
        with directory(self.root) as fd, self.budget.locked():
            current = self.view()
            if current['revision'] != view['revision']: raise ValueError('Image history changed; review again')
            self.settle(fd, current)
            stats = self.namespace(fd)
            if os.fstat(fd).st_dev != self.budget.root.stat().st_dev:
                raise ValueError('History and allocation lock must share the data filesystem')
            fs = os.fstatvfs(fd); block = fs.f_frsize or fs.f_bsize
            delta = rounded(len(raw), block) + rounded(MANIFEST_BYTES, block) + 4*block
            additional = 1
            if view['format'] == 1:
                delta += rounded(len(encode(view['active'])), block); additional += 1
            if stats['allocated']+delta > ALLOCATED or stats['objects']+additional > 16 or stats['entries']+additional+4 > ENTRIES or stats['metadata']+rounded(MANIFEST_BYTES, block)+4*block > METADATA_BYTES:
                raise ValueError('History publication peak exceeds finite envelope')
            self.budget.check(delta, additional+4, result=result)
            if plan is not None and view['format'] == 1:
                held = self.jobs.ledger_fd
                safe(os.fstat(held), 2 if pair(fd) else 1)
                if not pair(fd):
                    bound = os.stat('ledger.lock', dir_fd=fd, follow_symlinks=False)
                    if (bound.st_dev, bound.st_ino) != (os.fstat(held).st_dev, os.fstat(held).st_ino): raise ValueError('Ledger exclusion changed')
                    self.fault('fence-link'); os.link('ledger.lock', 'history-format-v2.lock', src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                    self.fault('fence-link-created')
                self.fault('fence-validate'); pair(fd, held, True)
                self.fault('fence-validated')
                self.sync(held, 'fence-file-fsync'); self.sync(fd, 'fence-directory-fsync'); self.parent_sync('fence-parent-fsync')
            if view['format'] == 1 and plan is None:
                # Explicit migration only. Legacy ordinary saves keep list format.
                temp = self.temporary(fd, 'manifest', raw)
                self.fault('manifest-replace'); os.replace(temp, 'jobs.json', src_dir_fd=fd, dst_dir_fd=fd)
                self.sync(fd, 'manifest-directory-fsync'); self.parent_sync('manifest-parent-fsync')
                self.fault('lost-ack'); return
            pair(fd, self.jobs.ledger_fd, True)
            archive = self.object(fd, encode(view['active']), len(view['active'])) if view['format'] == 1 else view['manifest']['active']
            active = self.object(fd, raw, len(rows))
            archives = [] if view['format'] == 1 else list(view['manifest']['archives'])
            if plan and plan['operation'] == 'rollover': archives.append(archive)
            token = dict(plan=plan, archive_sha256=archive['sha256']) if plan else view['manifest']['maintenance']
            manifest = dict(format_version=2, generation=1 if view['format'] == 1 else view['manifest']['generation']+1,
                            parent_revision=None if view['format'] == 1 else view['revision'],
                            active=active, archives=archives, maintenance=token)
            if manifest['generation'] >= 2**63: raise ValueError('History generation bound reached')
            payload = encode(manifest)
            if len(payload) > MANIFEST_BYTES or len(payload) + stats['metadata'] > METADATA_BYTES: raise ValueError('History metadata bound reached')
            temp = self.temporary(fd, 'manifest', payload)
            self.fault('manifest-replace'); os.replace(temp, 'jobs.json', src_dir_fd=fd, dst_dir_fd=fd)
            self.sync(fd, 'manifest-directory-fsync'); self.parent_sync('manifest-parent-fsync')
            self.settle(fd, self.view())
            self.fault('lost-ack')

    def completed(self, view, plan):
        token = view['manifest']['maintenance'] if view['format'] == 2 else None
        if not token or token['plan'] != plan: return None
        with directory(self.root) as fd, self.budget.locked(): self.settle(fd, view)
        return dict(message='History maintenance already completed; all identities retained.', revision=view['revision'])

    def apply(self, plan):
        validate_plan(plan)
        with self.jobs.lock('ledger.lock'):
            completed = self.completed(self.view(), plan)
            if completed: return completed
        with self.jobs.lock('worker.lock', True), self.jobs.lock('ledger.lock'):
            view = self.view()
            completed = self.completed(view, plan)
            if completed: return completed
            if self.review(view) != plan: raise ValueError('Image history changed; review maintenance again')
            self.publish(view, [] if plan['operation'] == 'rollover' else view['active'], plan)
            return dict(message='History maintenance completed; all identities retained.', revision=self.view()['revision'])
