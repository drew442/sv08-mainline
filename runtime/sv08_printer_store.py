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
from sv08_printer_definitions import builtins
from sv08_printer_compose import select_definition, migration_preview, remap_board, runtime_assets, catalog_for, remove_definition
from sv08_printer_sources import GitHub, accept_source, bundle_preview
from sv08_printer_publish import Publisher

STORAGE_LIMIT = 4 * 1024 * 1024
STATE_LIMIT = 2 * 1024 * 1024


class PrinterStore:
    def __init__(self, store, boot_path, config_view, catalog, privileged=lambda: os.geteuid() == 0, source_fetch=None, publication_admit=lambda:False,publication_validate=None):
        self.store, self.boot_path, self.config_view = store, Path(boot_path), Path(config_view)
        self.catalog, self.privileged = catalog, privileged
        self.source_fetch, self.publication_admit = source_fetch, publication_admit
        self.publication_validate=publication_validate

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
        created=not self.directory.exists()
        self.directory.mkdir(mode=0o700, exist_ok=True)
        if created:fsync_dir(self.directory.parent)
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
        if path.stat().st_size>STATE_LIMIT:raise ValueError('Stored envelope is oversized; original retained')
        value=strict_json(path.read_bytes(),STATE_LIMIT)
        if not isinstance(value,dict) or not {'format_version','revision','draft','current','previous'} <= set(value) or set(value)-{'format_version','revision','draft','current','previous','sources'}:
            raise ValueError('Corrupt configuration state; originals retained')
        if value['format_version']!=1:
            if writable:raise ValueError('Unsupported stored schema; export original for diagnosis')
            return value
        if type(value['revision']) is not int or value['revision']<0:
            raise ValueError('Corrupt revision; original retained')
        if writable:
            catalog_for(value['draft'],self.catalog).validate(value['draft'])
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
                           catalog=self.catalog.revision,sources=state.get('sources',{}),generator=GENERATOR_VERSION,
                           mode=mode,context=context))

    def definitions(self,state):
        rows=[]
        for record in builtins(self.catalog):
            rows.append(dict(record=record,reference=dict(source='builtin',id=record['id'],version=record['version'],sha256=digest(record),commit=self.catalog.revision),origin='Built-in'))
        for source in state.get('sources',{}).values():
            if not source['enabled']:continue
            for record in source['records']:
                rows.append(dict(record=record,reference=dict(source=source['id'],id=record['id'],version=record['version'],sha256=digest(record),commit=source['commit']),origin=source.get('repository','Local definition')))
        return rows

    def request(self, request):
        if not isinstance(request,dict) or 'action' not in request:
            raise ValueError('Invalid request')
        action=request['action']
        allowed={'status':{'action'},'save':{'action','expected_revision','draft'},
                 'review':{'action','mode'},'apply':{'action','mode','review'},
                 'restore':{'action','expected_revision'},'import':{'action','draft','expected_revision'},
                 'preset':{'action','draft','role','preset','expected_revision'},
                 'component':{'action','draft','role','preset','expected_revision'}}
        allowed.update({
            'migration':{'action','expected_revision'},
            'review_draft':{'action','draft','mode','expected_revision'},
            'board_preview':{'action','draft','role','board','expected_revision'},
            'definition':{'action','draft','reference','expected_revision'},
            'definition_remove':{'action','draft','reference','expected_revision'},
            'source_preview':{'action','url','ref','path','expected_revision'},
            'bundle_preview':{'action','bundle','expected_revision'},
            'source_add':{'action','source','expected_revision'},
            'source_check':{'action','source_id','expected_revision'},
            'source_disable':{'action','source_id','expected_revision'},
            'source_enable':{'action','source_id','expected_revision'},
            'source_remove':{'action','source_id','expected_revision'},
            'configuration_export':{'action','expected_revision','mode'},
            'publication_review':{'action','expected_revision'},
            'publication_apply':{'action','expected_revision','review'},
            'publication_restore_review':{'action','expected_revision'},
            'publication_restore':{'action','expected_revision','review'},
            'publication_reconcile':{'action','expected_revision'}})
        if action in allowed and action != 'status':
            allowed[action] = allowed[action] | {'expected_identity'}
        if action not in allowed or set(request)!=allowed[action]:
            raise ValueError('Unsupported finite helper operation')
        # Exact finite schemas include the identity of the last loaded status.
        with self.locked() as (context,record):
            state=self.load(writable=action!='status')
            if action=='status' and (state['format_version']!=1 or not isinstance(state.get('draft'),dict) or state['draft'].get('format_version')!=1):
                # Future envelopes are opaque diagnostic data, never composed.
                return dict(state=state,catalog=self.catalog.data,context=context,catalog_revision=self.catalog.revision,catalog_supported=self.catalog.supported,loaded_identity=digest(dict(state=state,context=context)),definitions=[],sources={},migration_available=False)
            available=[row['record'] for row in self.definitions(state)]
            effective=catalog_for(request.get('draft',state['draft']),self.catalog,available)
            if action=='status':
                return dict(state=state,catalog=effective.data,context=context,
                            catalog_revision=self.catalog.revision,catalog_supported=self.catalog.supported,
                            loaded_identity=self.identity(state,context,None),definitions=self.definitions(state),sources=state.get('sources',{}),migration_available='definition_plan' not in state['draft'])
            if 'expected_revision' in request:
                messages={'import':'importing','preset':'selecting defaults','component':'selecting hardware','save':'saving','restore':'saving'}
                if type(request['expected_revision']) is not int or request['expected_revision']!=state['revision']:
                    raise ValueError('Draft changed in another session; refresh before '+messages.get(action,'continuing'))
            if request['expected_identity'] != self.identity(state,context,None):
                raise ValueError('Loaded configuration context is stale; refresh before continuing')
            if action=='configuration_export':
                generated=generate(self.catalog,state['draft'],request['mode'])
                if not generated['complete']:raise ValueError('Configuration incomplete: '+ '; '.join(generated['blockers']))
                if 'files' not in generated:raise ValueError('Choose Setup or Full SV08 for a complete software bundle')
                if not self.publication_validate:raise ValueError('Pinned complete-output validator is unavailable')
                import tempfile,base64
                from sv08_printer_stack import archive
                with tempfile.TemporaryDirectory(prefix='sv08-config-export-') as directory:
                    preview=Publisher(directory).preview({'hardware.cfg':generated['text']},context,'export')
                    validation=self.publication_validate(preview,directory)
                    if not validation.get('validated'):raise ValueError('Complete-output validation failed')
                return dict(filename='sv08-printer-configuration.zip',data=base64.b64encode(archive(generated['files'])).decode(),validation=validation,printing_enabled=generated['printing_enabled'],setup_requirements=generated['setup_requirements'])
            if action=='review_draft':return dict(**generate(self.catalog,request['draft'],request['mode']),review=None,revision=state['revision'])
            if action=='migration':return migration_preview(state['draft'],self.catalog,builtins(self.catalog))
            if action=='board_preview':return remap_board(request['draft'],request['role'],request['board'],effective)
            if action=='definition_remove':return dict(draft=remove_definition(effective,request['draft'],request['reference']))
            if action=='definition':
                effective.validate(request['draft'])
                snapshots={}
                for row in self.definitions(state):
                    snapshots[row['reference']['source']+'::'+row['record']['id']+'@'+row['record']['version']]=row['record']
                return dict(draft=select_definition(effective,request['draft'],request['reference'],snapshots))
            if action=='source_preview':return GitHub(self.source_fetch).preview(request['url'],self.catalog,request['ref'],request['path'])
            if action=='bundle_preview':return bundle_preview(request['bundle'],self.catalog)
            if action=='source_check':
                source=state.get('sources',{}).get(request['source_id'])
                if not source or not source['enabled'] or source['origin']!='github':raise ValueError('No enabled GitHub source')
                return GitHub(self.source_fetch).preview(source['url'],self.catalog,source['ref'],source['path'])
            if action in ('source_add','source_disable','source_enable','source_remove'):
                sources=state.get('sources',{})
                if action=='source_add':
                    candidate=request['source']
                    if candidate.get('origin')=='github':
                        verified=GitHub(self.source_fetch).preview(candidate['url'],self.catalog,candidate['commit'],candidate['path'])
                        verified['ref']=candidate['ref']
                        if digest(verified)!=digest(candidate):raise ValueError('Source preview changed; preview again')
                    for retained in [state['draft'],*[c['draft'] for c in (state['current'],state['previous']) if c]]:
                        snapshots=retained.get('definition_plan',{}).get('snapshots',{})
                        for definition in candidate['records']:
                            key=candidate['id']+'::'+definition['id']+'@'+definition['version']
                            if key in snapshots and digest(snapshots[key])!=digest(definition):raise ValueError('Pinned version changed; author must bump version')
                    sources=accept_source(sources,candidate,self.catalog)
                else:
                    if request['source_id'] not in sources:raise ValueError('Unknown source')
                    sources=dict(sources)
                    if action in ('source_disable','source_enable'):sources[request['source_id']]={**sources[request['source_id']],'enabled':action=='source_enable'}
                    else:del sources[request['source_id']]
                state.update(sources=sources,revision=state['revision']+1);self.publish(state,record)
                return dict(revision=state['revision'],message='Definition source updated; selected snapshots unchanged')
            if action.startswith('publication_'):
                if action in ('publication_restore_review','publication_restore'):
                    publisher=Publisher(self.directory.parent,self.publication_admit,getattr(self.store,'budget',None),self.publication_validate)
                    if action=='publication_restore_review':return publisher.restore_preview(context)
                    return publisher.restore(request['review'],context)
                if action=='publication_reconcile':return Publisher(self.directory.parent,self.publication_admit,getattr(self.store,'budget',None),self.publication_validate).reconcile()
                if not state['current'] or state['current']['mode']!='full' or digest(state['current']['draft'])!=digest(state['draft']):raise ValueError('Save a complete full candidate for these selections before publication')
                generated=generate(self.catalog,state['draft'],'full')
                if not generated['complete'] or generated['text']!=state['current']['text']:raise ValueError('Candidate or definition lock changed; regenerate before publication')
                files={'hardware.cfg':generated['text']}
                publisher=Publisher(self.directory.parent,self.publication_admit,getattr(self.store,'budget',None),self.publication_validate)
                plan=self.identity(state,context,'full')
                if action=='publication_review':return publisher.preview(files,context,plan)
                result=publisher.apply(request['review'],files,context,plan)
                return dict(applied=True,receipt=result,message='Managed configuration applied; printer remains stopped. Commission changed components separately.')
            if action=='import':
                effective.validate(request['draft'])
                return dict(draft=request['draft'],changed=digest(request['draft'])!=digest(state['draft']),expected_revision=state['revision'])
            if action=='preset':
                return dict(draft=self.catalog.apply_preset(request['draft'],request['role'],request['preset']))
            if action=='component':
                return dict(draft=self.catalog.select_component(request['draft'],request['role'],request['preset']))
            if action in ('save','restore'):
                if action=='restore':
                    if not state['previous']:raise ValueError('No previous candidate')
                    draft=state['previous']['draft']
                else:draft=request['draft']
                catalog_for(draft,self.catalog,available).validate(draft)
                if 'definition_plan' in draft:
                    # Keep old assets unless an explicit new override requires a lock.
                    draft=json.loads(json.dumps(draft))
                    pinned=draft['definition_plan'].get('runtime_assets')
                    updated=runtime_assets(draft,catalog_for(draft,self.catalog,available))
                    if pinned:
                        old_curves={c['id']:c for c in pinned['curves']}
                        for c in updated['curves']:
                            if c['id'] in old_curves:c.update(old_curves[c['id']])
                        old_boards={b['id']:b for b in pinned['boards']}
                        updated['boards']=[old_boards.get(b['id'],b) for b in updated['boards']]
                    draft['definition_plan']['runtime_assets']=updated
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
