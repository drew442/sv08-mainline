"""Managed configuration publication: immutable bundle, one activation file.

No service start/restart, template evaluation, MCU access or output operation.
"""
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import grp
import stat
import tempfile
from sv08_state import atomic_json, fsync_dir
from sv08_printer_catalog import digest, encoded, strict_json, BUNDLE_LIMIT

MARKER = '# SV08 managed hardware configuration\n'
FILE_NAMES = {'hardware.cfg','behaviours.cfg','custom.cfg'}


def sha(raw):return hashlib.sha256(raw).hexdigest()

def regular(path,missing=False):
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Unexpected managed configuration link')
    if not path.exists():
        if missing:return None
        raise ValueError('Missing configuration file')
    st=path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_size>BUNDLE_LIMIT:raise ValueError('Invalid configuration file/type/size')
    return path.read_bytes()


def sections(text):
    # Klipper uses indented G-code/template bodies; configparser is only used for
    # structural ownership, never to evaluate templates or claim physical safety.
    parser=configparser.RawConfigParser(strict=True,interpolation=None)
    try:parser.read_string(text)
    except configparser.Error:raise ValueError('Invalid or duplicate configuration section') from None
    return set(parser.sections())


def inventory(root):
    """Account for the explicit include closure and SAVE_CONFIG byte drift."""
    found={};owned=set();visiting=set()
    def read(relative,depth=0):
        if depth>12 or len(found)>64:raise ValueError('Configuration include closure exceeds limit')
        if relative in visiting:raise ValueError('Configuration include cycle')
        if relative in found:return
        path=Path(relative)
        if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe configuration include')
        raw=regular(root/path,missing=relative=='printer.cfg')
        if raw is None:found[relative]=None;return
        if sum(len(x or b'') for x in found.values())+len(raw)>2*BUNDLE_LIMIT:raise ValueError('Configuration inventory exceeds limit')
        text=raw.decode();found[relative]=raw;visiting.add(relative)
        parser_sections=sections(text)
        for name in parser_sections:
            if name.startswith('include '):
                pattern=name[8:]
                if '*' in pattern or '?' in pattern or '[' in pattern:raise ValueError('Adopt wildcard includes explicitly before managed publication')
                read(str(path.parent/pattern),depth+1)
            else:
                if name in owned:raise ValueError('Duplicate section in include closure')
                owned.add(name)
        visiting.remove(relative)
    read('printer.cfg')
    return found,owned


class Publisher:
    def __init__(self,root,admit=lambda:False,budget=None,validate=None):
        self.root=Path(root);self.admit=admit;self.budget=budget;self.validate=validate
        self.directory=self.root/'printer-managed'
        try:self.reader_gid=grp.getgrnam('sv08').gr_gid if os.geteuid()==0 else os.getegid()
        except KeyError:self.reader_gid=os.getegid()
    def check_root(self):
        if not self.root.is_dir() or any(p.is_symlink() for p in (self.root,*self.root.parents)):raise ValueError('Invalid physical configuration root')
        if self.directory.is_symlink():raise ValueError('Unexpected managed bundle link')
    def receipt(self):
        self.check_root();path=self.directory/'receipt.json'
        raw=regular(path,missing=True)
        return strict_json(raw,BUNDLE_LIMIT) if raw else None
    def preview(self,files,context,plan_id):
        self.check_root()
        if set(files)-FILE_NAMES or 'hardware.cfg' not in files:raise ValueError('Unsupported managed destination')
        if sum(len(v.encode()) for v in files.values())>BUNDLE_LIMIT:raise ValueError('Managed output oversized')
        new_sections=set()
        for name,text in files.items():
            names=sections(text)
            if any(s.startswith('include ') or s.startswith('delayed_gcode ') for s in names):raise ValueError('Managed include/startup behaviour requires separate capability')
            if names&new_sections:raise ValueError('Conflicting managed section ownership')
            new_sections|=names
        current,current_sections=inventory(self.root);prior=self.receipt()
        if prior:
            # Every prior owned file and activation point participates in drift.
            for name,h in prior['after'].items():
                raw=regular(self.root/name,missing=h is None)
                if (sha(raw) if raw is not None else None)!=h:raise ValueError('Managed configuration drift; reconcile manual/SAVE_CONFIG edits')
            old_sections=set(prior['sections'])
        else:old_sections=set()
        unmanaged=current_sections-old_sections
        if unmanaged&new_sections:raise ValueError('Unmanaged section conflict; explicit ownership adoption required: '+', '.join(sorted(unmanaged&new_sections)))
        identity=digest(dict(context=context,plan=plan_id,files=files,before={n:sha(v) if v is not None else None for n,v in current.items()},receipt=prior))
        prefix=current.get('printer.cfg') or b''
        if MARKER.encode() in prefix:
            if not prior:raise ValueError('Unknown managed marker')
            if prefix.count(MARKER.encode())!=1:raise ValueError('Ambiguous activation marker')
            start=prefix.index(MARKER.encode());tail=prefix[start:].splitlines(keepends=True)
            if len(tail)<2 or not tail[1].startswith(b'[include printer-managed/'):raise ValueError('Managed activation marker changed')
            prefix=prefix[:start]+b''.join(tail[2:])
        include='printer-managed/'+identity+'/bundle.cfg'
        activation=prefix+(b'\n' if prefix and not prefix.endswith(b'\n') else b'')+MARKER.encode()+('[include '+include+']\n').encode()
        # Physical defaults and unresolved values must be resolved before this API.
        return dict(review=identity,files=files,activation=activation.decode(),before={n:sha(v) if v is not None else None for n,v in current.items()},sections=sorted(new_sections),context=context,plan=plan_id,previous_available=prior is not None,diff=[dict(path=n,before=None,after=v,operation='create immutable managed file') for n,v in sorted(files.items())]+[dict(path='printer.cfg',before=prefix.decode(),after=activation.decode(),operation='update activation include')],service_action='none; printer stays stopped')
    def apply(self,review,files,context,plan_id):
        if not self.admit():raise ValueError('Printer must be stopped and not printing; no publication')
        current=self.preview(files,context,plan_id)
        if not self.validate or not self.validate(current,self.root).get('validated'):raise ValueError('Complete-output validation is required before publication')
        if current['review']!=review or self.preview(files,context,plan_id)['review']!=review:raise ValueError('Publication review is stale')
        if self.directory.exists():
            st=self.directory.stat()
            if stat.S_IMODE(st.st_mode)!=0o750 or st.st_gid!=self.reader_gid or st.st_uid!=os.geteuid():raise ValueError('Managed directory must be private/owned')
        else:
            self.directory.mkdir(mode=0o750);os.chmod(self.directory,0o750);os.chown(self.directory,os.geteuid(),self.reader_gid);fsync_dir(self.root)
        if (self.directory/'journal.json').exists():raise ValueError('Unfinished publication: reconcile before retrying')
        existing=list(self.directory.rglob('*'))
        if len(existing)+len(files)+4>96 or sum(p.stat().st_size for p in existing if p.is_file())+sum(len(v.encode()) for v in files.values())+len(encoded(current))*2+8192>2*1024*1024:raise ValueError('Managed snapshot storage limit reached')
        required=sum(len(v.encode()) for v in files.values())+len(encoded(current))*2+8192
        fs=os.statvfs(self.root)
        if fs.f_bavail*fs.f_frsize<768*1024*1024+required or fs.f_favail<130:raise ValueError('Insufficient publication reserve')
        if self.budget:self.budget.check(required,8)
        destination=self.directory/current['review']
        if destination.exists():raise ValueError('Bundle already exists; reconcile prior publication')
        before=regular(self.root/'printer.cfg',missing=True)
        previous=self.receipt()
        before_metadata=metadata(self.root/'printer.cfg')
        journal=dict(status='prepared',review=current['review'],before=None if before is None else before.decode(),before_hash=None if before is None else sha(before),after_hash=sha(current['activation'].encode()),previous=previous,before_metadata=before_metadata)
        atomic_json(self.directory/'journal.json',journal)
        destination.mkdir(mode=0o750);os.chmod(destination,0o750);os.chown(destination,os.geteuid(),self.reader_gid);fsync_dir(self.directory)
        try:
            for name,text in files.items():put(destination/name,text.encode(),0o640,(os.geteuid(),self.reader_gid))
            put(destination/'bundle.cfg',''.join('[include '+name+']\n' for name in sorted(files)).encode(),0o640,(os.geteuid(),self.reader_gid))
            after={str((destination/name).relative_to(self.root)):sha(regular(destination/name)) for name in [*files,'bundle.cfg']}
            if not self.admit():raise ValueError('Printer stopped state changed during publication; reconcile inactive bundle')
            if self.preview(files,context,plan_id)['review']!=review:raise ValueError('Publication context changed during validation; reconcile before retrying')
            after['printer.cfg']=sha(current['activation'].encode())
            receipt=dict(format_version=1,review=review,after=after,sections=current['sections'],previous=previous,activation_before=journal['before'],activation_before_metadata=before_metadata,context=context,plan=plan_id,service_action='none',commissioning='required separately')
            if len(encoded(receipt))>BUNDLE_LIMIT:raise ValueError('Restoration receipt budget exceeded; reconcile before retrying')
            put_metadata(self.root/'printer.cfg',current['activation'].encode(),before_metadata or dict(mode=0o640,uid=os.geteuid(),gid=self.reader_gid))
            atomic_json(self.directory/'receipt.json',receipt)
            (self.directory/'journal.json').unlink();fsync_dir(self.directory)
            return receipt
        except BaseException:
            # The bundle is immutable/inactive until the single root activation.
            # Keep journal and bundle for reconciliation, never claim rollback.
            raise
    def restore_preview(self,context):
        prior=self.receipt()
        if not prior:raise ValueError('No applied configuration history')
        for name,h in prior['after'].items():
            if sha(regular(self.root/name))!=h:raise ValueError('Managed configuration drift; reconcile before restoration')
        return dict(review=digest(dict(receipt=prior,context=context)),before=regular(self.root/'printer.cfg').decode(),after=prior['activation_before'],previous=prior['previous'],after_metadata=prior.get('activation_before_metadata'),context=context,service_action='none; restoration does not restart printer')
    def restore(self,review,context):
        if not self.admit():raise ValueError('Printer must be stopped for restoration')
        preview=self.restore_preview(context)
        if preview['review']!=review:raise ValueError('Restoration review is stale')
        if (self.directory/'journal.json').exists():raise ValueError('Reconcile interrupted publication first')
        after=preview['after']
        journal=dict(status='restoring',review=review,before=preview['before'],before_hash=sha(preview['before'].encode()),after_hash=sha(after.encode()) if after is not None else None,previous=self.receipt(),before_metadata=metadata(self.root/'printer.cfg'))
        atomic_json(self.directory/'journal.json',journal)
        if after is None:(self.root/'printer.cfg').unlink();fsync_dir(self.root)
        else:put_metadata(self.root/'printer.cfg',after.encode(),preview['after_metadata'])
        if preview['previous']:atomic_json(self.directory/'receipt.json',preview['previous'])
        else:(self.directory/'receipt.json').unlink()
        (self.directory/'journal.json').unlink();fsync_dir(self.directory)
        return dict(restored=True,service_action='none',commissioning='Check prior configuration against newly fitted hardware')

    def reconcile(self):
        self.check_root();journal=strict_json(regular(self.directory/'journal.json'),BUNDLE_LIMIT)
        raw=regular(self.root/'printer.cfg',missing=True);h=sha(raw) if raw is not None else None
        if h not in (journal['before_hash'],journal['after_hash']):raise ValueError('Unexpected edits during interrupted publication')
        if not self.admit():raise ValueError('Printer must remain stopped for restoration')
        if journal['before'] is None:
            if raw is not None:(self.root/'printer.cfg').unlink();fsync_dir(self.root)
        else:put_metadata(self.root/'printer.cfg',journal['before'].encode(),journal.get('before_metadata'))
        if journal['previous']:atomic_json(self.directory/'receipt.json',journal['previous'])
        elif (self.directory/'receipt.json').exists():(self.directory/'receipt.json').unlink()
        (self.directory/'journal.json').unlink();fsync_dir(self.directory)
        return dict(restored=True,service_action='none',commissioning='review against fitted hardware')


def metadata(path):
    if not path.exists():return None
    st=path.stat();return dict(mode=stat.S_IMODE(st.st_mode),uid=st.st_uid,gid=st.st_gid)

def put_metadata(path,raw,meta):
    if not meta:raise ValueError('Missing original configuration permissions')
    put(path,raw,meta['mode'],(meta['uid'],meta['gid']))

def put(path,raw,mode,owner=None):
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:
            if owner:os.fchown(out.fileno(),*owner)
            os.fchmod(out.fileno(),mode);out.write(raw);out.flush();os.fsync(out.fileno())
        os.replace(name,path);fsync_dir(path.parent)
    finally:
        if os.path.exists(name):os.unlink(name)


def validate_output(preview,root,python='/opt/sv08-mainline/venvs/klipper-f0892d8/bin/python',klippy='/opt/sv08-mainline/klipper/klippy/klippy.py',dictionary='/usr/share/sv08/printer/validation/klipper.dict',*,private_diagnostics=None,isolated_children=False):
    """Validate the complete explicit include closure using simulated MCU output.

    Never submit G-code, connect a serial device or evaluate a publisher installer.
    The fixed pinned upstream process must reach ready through its private API.
    Unsupported startup/host-hardware extras refuse publication before invocation.
    private_diagnostics is an opt-in private callback, never a public API field.
    isolated_children asserts this caller has no unrelated reaped children.
    """
    import socket
    import subprocess
    import time
    expected='86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b'
    raw=regular(Path(dictionary))
    if sha(raw)!=expected:raise ValueError('Matching pinned validation dictionary is required')
    if not Path(python).is_file() or not Path(klippy).is_file():raise ValueError('Pinned Klipper validation runtime is unavailable')
    if sha(regular(Path(klippy)))!='aa9eb47fbe3598fc814d40ed8e0b2b814a0af459fca7acab6732c59bf42e4659':raise ValueError('Pinned Klipper entry point changed')
    current,_=inventory(Path(root))
    allowed={'printer','mcu','probe','extruder','heater_bed','bed_mesh','quad_gantry_level','respond','pause_resume','display_status','print_stats','virtual_sdcard','gcode_arcs','exclude_object','safe_z_home','display','adxl345'}
    prefixes=('mcu ','stepper_','tmc2209 ','temperature_sensor ','thermistor ','fan_generic ','heater_generic ','filament_switch_sensor ','gcode_macro ','heater_fan ','output_pin ','neopixel ','gcode_button ','verify_heater ','adxl345 ')
    combined=[v.decode() for v in current.values() if v]+list(preview['files'].values())
    for text in combined:
        for name in sections(text):
            if name.startswith('include '):continue
            if name not in allowed and not name.startswith(prefixes):raise ValueError('Complete-output validation does not support section '+name)
    with tempfile.TemporaryDirectory(prefix='sv08-config-validation-') as scratch:
        work=Path(scratch)
        for name,raw in current.items():
            if raw is None:continue
            path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        for name,text in preview['files'].items():
            path=work/'printer-managed'/preview['review']/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        if preview['files']:
            (work/'printer-managed'/preview['review']/'bundle.cfg').write_text(''.join('[include '+n+']\n' for n in sorted(preview['files'])))
        (work/'printer.cfg').write_text(preview['activation'])
        args=['/usr/bin/prlimit','--as=268435456','--cpu=8','--fsize=4194304','--',python,klippy,str(work/'printer.cfg'),'-a',str(work/'api'),'-o',str(work/'mcu.output'),'-d',str(dictionary),'-l',str(work/'klippy.log')]
        _,names=inventory(work)
        for name in sorted(names):
            if name.startswith('mcu '):args+=['-d',name[4:]+'='+str(dictionary)]
        # Private diagnostic consumers must own an isolated invocation before
        # interpreting RUSAGE_CHILDREN deltas. Popen remains the sole reaper.
        import resource
        usage_before=resource.getrusage(resource.RUSAGE_CHILDREN) if private_diagnostics and isolated_children else None
        started=time.monotonic();deadline=started+10
        diagnostic=dict(pid=None,effective_limits=None,vm_kib={},socket_observed=False,last_state=None,
                        returncode_before_cleanup=None,cleanup_signals=[],cgroup=None,argv=args,last_operation=None,progress_samples=[])
        def remaining():
            budget=deadline-time.monotonic()
            if budget<=0:raise ValueError('Complete-output validation did not reach ready within budget')
            return budget
        def sample(final=False):
            if private_diagnostics is None:return
            proc=Path('/proc')/str(process.pid)
            progress=diagnostic['progress_samples'];elapsed=time.monotonic()-started
            # Reserve one final observation. Regular observations are spaced
            # across the existing deadline, with at most 32 records total.
            if final or (len(progress)<31 and (not progress or elapsed-progress[-1]['guest_elapsed']>=10/31)):
                row=dict(guest_elapsed=elapsed,child_state=None,kernel_accounted_cpu_ticks=None,
                         clock_ticks_per_second=os.sysconf('SC_CLK_TCK'),wchan=None,io=None)
                try:
                    # comm may contain spaces or ')'; fields after its final
                    # delimiter start at state (field 3), utime/stime are 14/15.
                    fields=(proc/'stat').read_text()[:4096].rpartition(')')[2].split()
                    row['child_state']=fields[0]
                    row['kernel_accounted_cpu_ticks']=dict(user=int(fields[11]),system=int(fields[12]))
                except (OSError,ValueError,IndexError):pass
                try:row['wchan']=(proc/'wchan').read_text()[:256].strip() or None
                except OSError:pass
                try:
                    counters={}
                    for line in (proc/'io').read_text()[:4096].splitlines():
                        key,_,value=line.partition(':')
                        if key in ('rchar','wchar','syscr','syscw','read_bytes','write_bytes','cancelled_write_bytes'):
                            counters[key]=int(value)
                    row['io']=counters or None
                except (OSError,ValueError):pass
                if len(progress)<32:progress.append(row)
                else:progress[-1]=row
            # /proc can disappear at any instant. Missing observations are not
            # evidence of zero usage or of a particular termination cause.
            try:
                limits=(proc/'limits').read_text()[:8192]
                expected_limits={'Max cpu time':['8','8'],'Max address space':['268435456','268435456'],'Max file size':['4194304','4194304']}
                if all(any(line.startswith(name) and line.split()[3:5]==values for line in limits.splitlines()) for name,values in expected_limits.items()):
                    diagnostic['effective_limits']=limits
                status=(proc/'status').read_text()[:16384]
                for line in status.splitlines():
                    key,_,value=line.partition(':')
                    if key in ('VmSize','VmPeak','VmRSS','VmHWM'):
                        diagnostic['vm_kib'][key]=max(diagnostic['vm_kib'].get(key,0),int(value.split()[0]))
                membership=(proc/'cgroup').read_text()[:4096]
                unified=next((line[3:] for line in membership.splitlines() if line.startswith('0::')),None)
                if unified is not None and '..' not in Path(unified).parts:
                    base=Path('/sys/fs/cgroup')/unified.lstrip('/')
                    events={}
                    for leaf in ('memory.events','memory.events.local'):
                        try:events[leaf]={key:int(value) for key,value in (line.split() for line in (base/leaf).read_text()[:4096].splitlines())}
                        except (OSError,ValueError):pass
                    if diagnostic['cgroup'] is None:
                        diagnostic['cgroup']=dict(path=unified,baseline=events,last=events)
                    elif diagnostic['cgroup']['path']==unified:diagnostic['cgroup']['last']=events
            except (OSError,ValueError):pass
            diagnostic['socket_observed'] |= (work/'api').exists()
        with (work/'stdout.log').open('wb') as log:
            process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,env={**os.environ,'MALLOC_ARENA_MAX':'1','PYTHONDONTWRITEBYTECODE':'1'})
            diagnostic['pid']=process.pid
            try:
                while True:
                    remaining();sample()
                    if process.poll() is not None:
                        raise ValueError('Complete-output validation process stopped before ready ('+str(process.returncode)+')')
                    if (work/'api').exists():
                        try:
                            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as api:
                                diagnostic['last_operation']='connect'
                                api.settimeout(min(1,remaining()));api.connect(str(work/'api'))
                                diagnostic['last_operation']='send'
                                api.settimeout(min(1,remaining()));api.sendall(b'{"id":1,"method":"info","params":{}}\x03')
                                reply=b''
                                while b'\x03' not in reply and len(reply)<32768:
                                    diagnostic['last_operation']='recv'
                                    api.settimeout(min(1,remaining()));chunk=api.recv(min(4096,32768-len(reply)))
                                    if not chunk:raise ValueError('Validation API ended before response')
                                    reply+=chunk
                            message=json.loads(reply.split(b'\x03',1)[0]);state=message.get('result',{}).get('state')
                            diagnostic['last_state']=state
                            if state=='ready':
                                remaining()
                                return dict(validated=True,klipper_revision='f0892d82b0f1c1228454f09eb508eddde2250f4b',dictionary_sha256=expected,physical_hardware=False)
                            if state in ('error','shutdown'):raise ValueError('Complete-output validation failed; inspect configuration before publication')
                        except (OSError,json.JSONDecodeError):pass
                    time.sleep(min(.05,remaining()))
            finally:
                sample(final=True)
                diagnostic['guest_elapsed_before_cleanup']=time.monotonic()-started
                diagnostic['returncode_before_cleanup']=process.poll()
                if diagnostic['returncode_before_cleanup'] is None:
                    try:process.terminate();diagnostic['cleanup_signals'].append('TERM')
                    except ProcessLookupError:pass
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:process.kill();diagnostic['cleanup_signals'].append('KILL')
                    except ProcessLookupError:pass
                    process.wait()
                if private_diagnostics is not None:
                    diagnostic['returncode_after_cleanup']=process.returncode
                    if usage_before is not None:
                        usage=resource.getrusage(resource.RUSAGE_CHILDREN)
                        diagnostic['isolated_child_cpu_seconds']=dict(user=usage.ru_utime-usage_before.ru_utime,system=usage.ru_stime-usage_before.ru_stime)
                    cgroup=diagnostic['cgroup']
                    if cgroup:
                        # Re-read the same actual child membership after reaping.
                        for leaf,baseline in cgroup['baseline'].items():
                            try:cgroup['last'][leaf]={key:int(value) for key,value in (line.split() for line in (Path('/sys/fs/cgroup')/cgroup['path'].lstrip('/')/leaf).read_text()[:4096].splitlines())}
                            except (OSError,ValueError):pass
                        cgroup['delta']={leaf:{key:cgroup['last'].get(leaf,{}).get(key,value)-value for key,value in values.items()} for leaf,values in cgroup['baseline'].items()}
                    diagnostic['private_log_excerpts']={}
                    for leaf in ('stdout.log','klippy.log'):
                        try:
                            with (work/leaf).open('rb') as stream:
                                stream.seek(0,2);size=stream.tell();stream.seek(max(0,size-8192))
                                diagnostic['private_log_excerpts'][leaf]=stream.read(8192).decode(errors='replace')
                        except OSError:pass
                    # A broken private sink cannot mask a validation failure or
                    # affect acceptance/cleanup. The probe checks capture itself.
                    try:private_diagnostics(diagnostic)
                    except Exception:pass
