"""Generation-local single-envelope publication with Store-before-feature locking.

Single atomic replacement commits draft/current/previous coherently. No replay or
permission ledger: reviews are ordinary hashes of the current content/context.
"""
from contextlib import contextmanager, nullcontext
import fcntl
import json
import os
from pathlib import Path
import stat
from sv08_state import atomic_json, fsync_dir
from sv08_printer_catalog import encoded, digest, strict_json, empty_draft, BUNDLE_LIMIT
from sv08_printer_generate import generate, GENERATOR_VERSION

STORAGE_LIMIT = 4 * 1024 * 1024
STATE_LIMIT = 2 * 1024 * 1024


class PrinterStore:
    def __init__(self, store, boot_path, config_view, catalog, privileged=lambda: os.geteuid() == 0):
        self.store, self.boot_path, self.config_view = store, Path(boot_path), Path(config_view)
        self.catalog, self.privileged = catalog, privileged

    def context(self):
        if not self.privileged():
            raise ValueError('Administrator access is required')
        if self.boot_path.is_symlink():
            raise ValueError('Unexpected boot context link')
        boot = strict_json(self.boot_path.read_bytes())
        state = self.store.load()
        if boot.get('trial') is not False or boot.get('slot') not in ('A','B') or boot.get('mode') not in ('immutable','writable'):
            raise ValueError('Unknown or trial generation context')
        if state.get('pending') and state['pending']['phase'] == 'trial':
            raise ValueError('Trial state is not configurable')
        record = state['slots'].get(boot['slot'])
        if not record or record['release'] != boot.get('release') or record['schema'] != 1:
            raise ValueError('Boot and state registry disagree')
        generation = self.store.generation_path(record)
        if str(generation) != boot.get('generation'):
            raise ValueError('Boot generation changed')
        config = generation / 'config'
        if config.is_symlink() or not config.is_dir():
            raise ValueError('Invalid generation configuration directory')
        # The view itself is the one intentional upstream integration symlink.
        if any(p.is_symlink() for p in self.config_view.parents):
            raise ValueError('Unexpected configuration view ancestry')
        if not self.config_view.is_symlink() or os.readlink(self.config_view) != str(config):
            raise ValueError('Configuration view does not match active generation')
        self.directory = config / 'printer-hardware'
        identity = dict(slot=boot['slot'],release=boot['release'],generation=str(generation),
                        mode=boot['mode'],boot_id=boot.get('boot_id'))
        return identity, record

    def safe_owned(self):
        if self.directory.is_symlink():
            raise ValueError('Unexpected owned directory link')
        self.directory.mkdir(mode=0o700, exist_ok=True)
        info=self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o700 or info.st_uid!=os.geteuid():
            raise ValueError('Feature directory must be private and owned')
        for p in self.directory.iterdir():
            st=p.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o600:
                raise ValueError('Unexpected file/link/mode in feature storage')
            if p.name not in ('.lock','state.json') and not p.name.startswith('.state.json.'):
                raise ValueError('Unexpected file in feature storage; originals retained')

    @contextmanager
    def locked(self):
        with self.store.locked(nonblocking=True):
            context, record=self.context()
            self.safe_owned()
            fd=os.open(self.directory/'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            try:
                try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:raise ValueError('Printer configuration is busy; refresh') from None
                self.safe_owned()
                yield context, record
            finally:os.close(fd)

    def load(self, writable=True):
        path=self.directory/'state.json'
        if not path.exists():
            return dict(format_version=1,revision=0,draft=empty_draft(),current=None,previous=None)
        value=strict_json(path.read_bytes(),STATE_LIMIT)
        if not isinstance(value,dict) or set(value)!= {'format_version','revision','draft','current','previous'}:
            raise ValueError('Corrupt configuration state; originals retained')
        if value['format_version']!=1:
            if writable:raise ValueError('Unsupported stored schema; export original for diagnosis')
            return value
        if type(value['revision']) is not int or value['revision']<0:
            raise ValueError('Corrupt revision; original retained')
        if writable:
            self.catalog.validate(value['draft'])
            for candidate in (value['current'],value['previous']):
                if candidate is not None:
                    if not isinstance(candidate,dict) or set(candidate)!={'draft','mode','text','catalog','generator','id'}:
                        raise ValueError('Corrupt candidate; original retained')
                    unsigned={k:v for k,v in candidate.items() if k!='id'}
                    if candidate['id']!=digest(unsigned) or len(candidate['text'].encode())>BUNDLE_LIMIT:
                        raise ValueError('Corrupt candidate content; original retained')
        return value

    def publish(self, value, record):
        raw=(json.dumps(value,indent=2,allow_nan=False)+"\n").encode()
        if len(raw)>STATE_LIMIT:raise ValueError('Configuration envelope is too large')
        fs=os.statvfs(self.directory);block=fs.f_frsize or fs.f_bsize
        round_block=lambda n:((n+block-1)//block)*block
        entries=list(self.directory.iterdir())
        # Include allocated blocks, sparse expansion, abandoned temps and directory.
        used=block+sum(max(p.stat().st_blocks*512,round_block(p.stat().st_size)) for p in entries)
        delta=round_block(len(raw))
        if used+delta>STORAGE_LIMIT or len(entries)+2>32:
            raise ValueError('Printer storage limit reached; prior state retained')
        allowance=self.store.check_copy_budget(record,reserve_full_copy=True)
        # Projected copy must also fit the existing allowance after publication.
        if allowance['copy_bytes']+delta>self.store.copy_limit_bytes:
            raise ValueError('State-copy allowance would be exceeded')
        budget=getattr(self.store,'budget',None)
        with budget.locked() if budget else nullcontext():
            if budget:
                budget.check(delta,2)
            elif fs.f_bavail*block < self.store.reserve_bytes+self.store.copy_limit_bytes+delta or fs.f_favail < allowance['copy_inodes']+130:
                raise ValueError('Insufficient shared reserve space or inodes')
            atomic_json(self.directory/'state.json',value)
        # Only safe abandoned publications are removed after a durable commit.
        for p in self.directory.glob('.state.json.*'):p.unlink()
        fsync_dir(self.directory)

    def identity(self, state, context, mode):
        return digest(dict(revision=state['revision'],draft=state['draft'],
                           current=state['current']['id'] if state['current'] else None,
                           catalog=self.catalog.revision,generator=GENERATOR_VERSION,
                           mode=mode,context=context))

    def request(self, request):
        if not isinstance(request,dict) or 'action' not in request:
            raise ValueError('Invalid request')
        action=request['action']
        allowed={'status':{'action'},'save':{'action','expected_revision','draft'},
                 'review':{'action','mode'},'apply':{'action','mode','review'},
                 'restore':{'action','expected_revision'},'import':{'action','draft'}}
        if action not in allowed or set(request)!=allowed[action]:
            raise ValueError('Unsupported finite helper operation')
        with self.locked() as (context,record):
            state=self.load(writable=action!='status')
            if action=='status':
                return dict(state=state,catalog=self.catalog.data,context=context,
                            catalog_revision=self.catalog.revision)
            if action=='import':
                self.catalog.validate(request['draft'])
                return dict(draft=request['draft'],changed=digest(request['draft'])!=digest(state['draft']),expected_revision=state['revision'])
            if action in ('save','restore'):
                if type(request['expected_revision']) is not int or request['expected_revision']!=state['revision']:
                    raise ValueError('Draft changed in another session; refresh before saving')
                if action=='restore':
                    if not state['previous']:raise ValueError('No previous candidate')
                    draft=state['previous']['draft']
                else:draft=request['draft']
                self.catalog.validate(draft)
                state.update(draft=draft,revision=state['revision']+1)
                self.publish(state,record)
                return dict(revision=state['revision'],message='Draft saved' if action=='save' else 'Previous draft restored; review before applying')
            generated=generate(self.catalog,state['draft'],request['mode'])
            identity=self.identity(state,context,request['mode'])
            if action=='review':return dict(**generated,review=identity,revision=state['revision'])
            if not generated['complete']:raise ValueError('Candidate is incomplete; review missing fields')
            if request['review']!=identity:raise ValueError('Review is stale; refresh and review again')
            candidate=dict(draft=state['draft'],mode=request['mode'],text=generated['text'],catalog=self.catalog.revision,generator=GENERATOR_VERSION)
            candidate['id']=digest(candidate)
            state.update(previous=state['current'],current=candidate,revision=state['revision']+1)
            self.publish(state,record)
            return dict(revision=state['revision'],candidate_id=candidate['id'],message='Candidate saved — inactive')
