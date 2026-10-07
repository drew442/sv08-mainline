#!/usr/bin/env python3
"""Exact additive printer package staging into a disposable root. No activation.

Overlay requires a caller-supplied complete file/mode inventory of the reviewed
host closure. Restoration checks every afterimage before restoring one host file.
"""
import argparse
from contextlib import contextmanager
import fcntl
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
from definition_repository_template import archive as repository_archive, FILENAME as REPOSITORY_ARCHIVE, schema_archive, SCHEMA_FILENAME

REPO=Path(__file__).resolve().parents[1]
NAV=b'<a href="../sv08-printer/index.html">Printer hardware</a>'
KNOWN_HOST={'app.js': ['eed0e2d76d8256f2a9fd590aefd47790f99b99511d9258358700f1825f47def4', 'feadb60128aba22ed0d7b61936ebd8e94fbeb6269173ca81ac7d7427a4d75b10'], 'upload.js': ['15cfc6d17922e78a9b60885d99e6742608ffc397e6e84109dcb93bf47370aeb7']}
KNOWN_PRINTER={'app.js': 'ead2fcd9912e29e662ab23a168fa1d3a3413ba5b59ff07bf8e0c708f4db6ec1d', 'index.html': '3683c8deb1d61d17e9ff167551718b83da470b913ff29135013a16779b0a66eb', 'manifest.json': 'acde271ee7268e45f8c08f5cc267041b6f40913c3537fc533d91382c69df639e', 'session.js': 'a5e70c69b2093ea1439b0ffc93fbf566130744ab51290603be0747c24629e3ef', 'style.css': '1c51b45172e157ccf46ebe3bc3ea8f451f2c2187b8b6754318826644bd78eeec'}
ANCHOR=b'<p class="eyebrow">YOUR PRINTER</p>'


@contextmanager
def root_lock(root):
    """Serialize supported offline writers on the stable root directory inode.

    The caller exclusively owns this root and must not rename/replace it or run
    uncooperative writers. No lock file is created, removed or recreated.
    """
    fd=os.open(root,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Offline root busy; no mutation') from None
        yield
    finally:os.close(fd)


def check_snapshot(root, expected, temporary=None):
    for name, metadata in expected.items():
        path=safe(root,name)
        if metadata is None:
            if path.exists() or path.is_symlink():raise ValueError('Filesystem drift; operation refused')
        elif not path.exists() or inventory(root,[name])[name]!=metadata:
            raise ValueError('Filesystem drift; operation refused')
        if metadata is not None and metadata['kind']=='directory':
            children={Path(n).name for n,m in expected.items() if m is not None and str(Path(n).parent)==name}
            if temporary is not None and temporary.parent==path:children.add(temporary.name)
            if {child.name for child in path.iterdir()}!=children:raise ValueError('Directory inventory drift; operation refused')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def safe(root, relative):
    parts=Path(relative).parts
    if Path(relative).is_absolute() or '..' in parts:raise ValueError('Invalid staging path')
    target=root/relative
    for p in (target,*target.parents):
        if p==root.parent:break
        if p.is_symlink():raise ValueError('Unexpected staging link')
    return target


def inventory(root, names):
    result={}
    for name in names:
        path=safe(root,name)
        if not path.exists():raise ValueError('Missing exact closure path: '+name)
        st=path.stat();entry=dict(mode=stat.S_IMODE(st.st_mode),uid=st.st_uid,gid=st.st_gid)
        if path.is_file():
            if st.st_nlink!=1:raise ValueError('Unexpected staging hardlink')
            entry.update(kind='file',sha256=sha(path.read_bytes()))
        elif path.is_dir():entry['kind']='directory'
        else:raise ValueError('Unsupported staging path kind')
        result[name]=entry
    return result


def dependencies(root, files):
    pending=['sv08_printer_helper'];seen={}
    while pending:
        module=pending.pop()
        if module in seen:continue
        name='usr/lib/sv08/'+module+'.py'
        raw=files.get(name)
        if raw is None:raw=safe(root,name).read_bytes()
        seen[name]=sha(raw)
        for node in ast.walk(ast.parse(raw)):
            modules=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            pending.extend(m for m in modules if m and m.startswith('sv08_') and 'usr/lib/sv08/'+m+'.py' not in seen)
    return seen


def payload(validation_dictionary=None):
    result={}
    for directory,target in [('ui/printer','usr/share/cockpit/sv08-printer'),('catalog/printer','usr/share/sv08/printer')]:
        for p in sorted((REPO/directory).rglob('*')):
            if p.is_file() and p.name!='session.js':result[target+'/'+str(p.relative_to(REPO/directory))]=p.read_bytes()
    for p in sorted((REPO/'runtime').glob('sv08_printer_*.py')):result['usr/lib/sv08/'+p.name]=p.read_bytes()
    if validation_dictionary is not None:
        path=Path(validation_dictionary)
        if path.is_symlink() or not path.is_file() or path.stat().st_size>128*1024:raise ValueError('Invalid validation dictionary')
        raw=path.read_bytes()
        if sha(raw)!='86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b':raise ValueError('Validation dictionary revision mismatch')
        result['usr/share/sv08/printer/validation/klipper.dict']=raw
    result['usr/share/cockpit/sv08-printer/'+REPOSITORY_ARCHIVE]=repository_archive(REPO)
    result['usr/share/cockpit/sv08-printer/'+SCHEMA_FILENAME]=schema_archive(REPO)
    return result


def replace_once(raw, before, after):
    if raw.count(before) != 1: raise ValueError('Unknown or ambiguous integration anchor')
    return raw.replace(before, after, 1)


def compose_host(raw, panel=None):
    """Compile the persistent panel; never fetch markup in the browser."""
    if panel is None: panel=(REPO/'ui/printer/panel.html').read_bytes()
    raw=replace_once(raw,NAV,b'<button data-page="printer">Printer hardware</button><button data-page="printer-connections">Connections</button><button data-page="definitions">Definitions</button><button data-page="definition-sources">Definition sources</button>')
    raw=replace_once(raw,b'<div id="notice"',b'<div data-host-status id="notice"')
    raw=replace_once(raw,b'<article class="card" aria-live="polite">',b'<article data-host-status class="card" aria-live="polite">')
    raw=replace_once(raw,b'</main>',b'<!-- printer panel -->'+panel+b'<!-- /printer panel -->\n</main>')
    if b'src="navigation.js"' not in raw:raw=replace_once(raw,b'<script defer src="app.js"></script>',b'<script defer src="navigation.js"></script><script defer src="app.js"></script>')
    return replace_once(raw,b'</head>',b'<link rel="stylesheet" href="../sv08-printer/style.css"><script defer src="../sv08-printer/app.js"></script></head>')


def integrate_app(raw):
    """Narrow patch: all unrelated installed host bytes are retained."""
    if raw.count(b'function page(name, focus = true) {')!=1:raise ValueError('Ambiguous host route anchor')
    start=raw.find(b'function page(name, focus = true) {')
    end=raw.find(b'function capability(',start)
    if start<0 or end<0: raise ValueError('Unknown host route anchor')
    original=raw[start:end]
    if original.count(b'function ')!=1: raise ValueError('Ambiguous host route anchor')
    raw=replace_once(raw,original,original.replace(b'function page(name, focus = true) {',b'function page(name, focus = true) {\n    if (window.sv08Navigation) { sv08Navigation.go(name); return; }',1))
    selector=b'main button:not([data-open]):not(#retry-submission):not([data-inspect-job])'
    if raw.count(selector)!=2: raise ValueError('Unknown host isolation anchors')
    raw=raw.replace(selector,selector+b':not(#printer button):not(#definition-sources button):not(#printer-connections button):not(#definitions button)')
    raw=replace_once(raw,b"} catch (error) { $('connection').textContent",b"} catch (error) { if (generation !== authorityGeneration) return; $('connection').textContent")
    # Navigation invalidates pending host plans using the existing response epoch.
    return replace_once(raw,b"window.addEventListener('sv08-authority-changed', () => {",b"window.addEventListener('sv08-navigation-changed', () => { ++authorityGeneration; plan = null; if ($('review').open) $('review').close('cancel'); });\nwindow.addEventListener('sv08-authority-changed', () => {")


def integrate_upload(raw):
    return replace_once(raw,b"window.addEventListener('sv08-authority-changed', () => {",b"window.addEventListener('sv08-navigation-changed', () => { ++authorityGeneration; uploadReview = null; if ($('upload-review').open) $('upload-review').close('cancel'); });\nwindow.addEventListener('sv08-authority-changed', () => {")


STYLE_EXTENSION=b'\n/* Shared panel intrinsic sizing and narrow header. */\n.layout{grid-template-columns:230px minmax(0,1fr)}main,nav{min-width:0}@media(max-width:800px){.layout{grid-template-columns:minmax(0,1fr)}}@media(max-width:500px){header{height:auto;min-height:72px;flex-wrap:wrap;gap:8px;padding:16px 20px}.header-end{flex-wrap:wrap}}\n'


def integrate_style(raw):
    if sha(raw)!='48c7b299dba9b7a76b94b7a8b19317f193d51b589cbcb1ba5c09373bd6192d32':raise ValueError('Unknown host style preimage')
    return raw+STYLE_EXTENSION


def stage(root, expected, execute=False, fresh=False, validation_dictionary=None):
    with root_lock(root):
        return _stage(root, expected, execute, fresh,validation_dictionary)


def _stage(root, expected, execute=False, fresh=False,validation_dictionary=None):
    root=Path(root).absolute()
    if not root.is_dir() or root.is_symlink():raise ValueError('Expected disposable root')
    check_snapshot(root,expected)
    required={'usr/lib/sv08/sv08_state.py','usr/lib/sv08/admin-context.json','etc/cockpit/cockpit.conf','usr/share/cockpit/sv08-host/index.html','usr/share/cockpit/sv08-host/session.js','usr/share/cockpit/sv08-host/app.js','usr/share/cockpit/sv08-host/upload.js','usr/share/cockpit/sv08-host/manifest.json'}
    if not isinstance(expected,dict) or not required<=set(expected):raise ValueError('Exact reviewed closure inventory is required')
    files=payload(validation_dictionary)
    closure=dependencies(root,files)
    required.update(name for name in closure if name not in files)
    if not required<=set(expected):raise ValueError('Missing reviewed Python dependency closure')
    # All existing ancestry participates in the exact directory-mode/owner guard.
    for name in list(required):
        parent=Path(name).parent
        while str(parent)!='.':
            if str(parent) not in expected:raise ValueError('Missing reviewed directory preimage: '+str(parent))
            parent=parent.parent
    for name in files:
        for parent in Path(name).parents:
            if str(parent)!='.' and safe(root,str(parent)).exists() and str(parent) not in expected:
                raise ValueError('Missing reviewed payload-parent directory preimage: '+str(parent))
    # Only read-only input closure; no helper/config file is refreshed.
    if inventory(root,expected)!=expected:raise ValueError('Exact preimage or mode mismatch')
    if (root/'usr/lib/sv08/admin-context.json').read_text().strip()!='{"format_version": 1, "context": "host"}':
        if json.loads((root/'usr/lib/sv08/admin-context.json').read_text())!={'format_version':1,'context':'host'}:raise ValueError('Unsupported context')
    if (root/'etc/cockpit/cockpit.conf').read_bytes()!=b'[WebService]\nShell=/sv08-host/index.html\n':raise ValueError('Unsupported custom Shell')
    packages=root/'usr/share/cockpit'
    if any(p.name not in {'base1','static','branding','issue','motd','sv08-host','sv08-printer'} for p in packages.iterdir()):raise ValueError('Unexpected package inventory')
    host='usr/share/cockpit/sv08-host/'
    before=safe(root,host+'index.html').read_bytes()
    if sha(before) not in ['ed0cadd8d49eb6371286ba37d22ce1de52487433db7211090d63dc42ce0aa095', '31511f59b81930634dec42005332fefc1036b9ef3935d9aebced60db0cc7d48a', '3529c93ddbe866d58a9d291b3e5f84c97417aacfef07d37fd0487761c24f8e92'] and before not in ((REPO/'ui/host/index.html').read_bytes(),(REPO/'ui/host/index.html').read_bytes().replace(NAV,b'')):raise ValueError('Unknown host HTML preimage')
    if NAV not in before:
        before=replace_once(before,ANCHOR,ANCHOR+b'\n'+NAV)
    files[host+'index.html']=compose_host(before)
    files[host+'navigation.js']=(REPO/'ui/host/navigation.js').read_bytes()
    for name,transform in [('app.js',integrate_app),('upload.js',integrate_upload),('style.css',integrate_style)]:
        original=safe(root,host+name).read_bytes()
        current=(REPO/'ui/host'/name).read_bytes()
        if original==current: files[host+name]=original
        else:
            if name!='style.css' and sha(original) not in KNOWN_HOST[name]: raise ValueError('Unknown host '+name+' preimage')
            files[host+name]=transform(original)
    owner=safe(root,'usr/lib/sv08/sv08_state.py').stat()
    originals={};after={};directories={}
    for name,raw in files.items():
        path=safe(root,name)
        if path.exists():
            if name not in expected:raise ValueError('Missing reviewed payload preimage: '+name)
            # Backend/catalog are unchanged closure, never refreshed in an overlay.
            if not name.startswith('usr/share/cockpit/') and path.read_bytes()!=raw:raise ValueError('Backend/catalog mismatch')
            if name.startswith('usr/share/cockpit/sv08-printer/') and path.read_bytes()!=raw and sha(path.read_bytes())!=KNOWN_PRINTER.get(path.name):raise ValueError('Unknown printer asset preimage')
            originals[name]=path.read_bytes().hex()
            after[name]=dict(expected[name],sha256=sha(raw))
        else:
            after[name]=dict(kind='file',sha256=sha(raw),mode=0o644,uid=owner.st_uid,gid=owner.st_gid)
        parent=Path(name).parent
        while str(parent)!='.' and not safe(root,str(parent)).exists():
            directories[str(parent)]=dict(kind='directory',mode=0o755,uid=owner.st_uid,gid=owner.st_gid);parent=parent.parent
    report=dict(format_version=3,activated=False,before=expected,after=after,originals=originals,new_directories=directories,dependency_closure=closure,
                payload_bytes=sum(map(len,files.values())),feature_storage_limit=4*1024*1024,
                peak_blocks_4096=sum((len(raw)+4095)//4096 for raw in files.values())+sum((len(bytes.fromhex(raw))+4095)//4096 for raw in originals.values()),
                root_delta_bytes=sum(len(raw)-(len(bytes.fromhex(originals[name])) if name in originals else 0) for name,raw in files.items()),
                largest_temporary_bytes=max(map(len,files.values()),default=0),
                added_inodes=len(set(files)-set(expected))+len(directories),publication='per-file atomic; host index published last')
    # Conservative allocation bounds, not statvfs admission. Backups are hex in
    # one retained report on /data; allow a second report copy during publication.
    block=lambda size:(size+4095)//4096
    report_bound=len(json.dumps(report,indent=2).encode())+8192
    report['capacity']=dict(block_size=4096,
        root_peak_increment_blocks=sum(block(len(raw)) for raw in files.values())+len(directories)+block(report['largest_temporary_bytes']),
        root_peak_increment_inodes=report['added_inodes']+1,
        data_report_bytes_upper_bound=report_bound,
        data_peak_increment_blocks=2*block(report_bound)+1,
        data_peak_increment_inodes=3,
        boot_peak_increment_blocks=0,boot_peak_increment_inodes=0,
        root_temporary_inodes=1,data_retained_report_inodes=1,data_report_temporary_inodes=1,
        backup_bytes_in_report=sum(len(raw) for raw in originals.values()),
        assumptions='one report plus publication temporary in one new /data directory; no separate backup files; exclusive offline root; no deployment packet included')
    if len(json.dumps(report,indent=2).encode())>report_bound:raise ValueError('Report accounting bound exceeded')
    if report['payload_bytes']>report['feature_storage_limit']:raise ValueError('Feature payload exceeds limit')
    if execute:
        snapshot=dict(expected)
        snapshot.update({name:None for name in set(after)|set(directories) if name not in expected})
        check_snapshot(root,snapshot)
        for name in files:
            temporary=safe(root,name).with_name(Path(name).name+'.integration-tmp')
            if temporary.exists() or temporary.is_symlink():raise ValueError('Unexpected publication temporary')
        for name,metadata in sorted(directories.items(),key=lambda item:len(Path(item[0]).parts)):
            check_snapshot(root,snapshot)
            path=safe(root,name);path.mkdir();path.chmod(metadata['mode']);os.chown(path,metadata['uid'],metadata['gid']);snapshot[name]=metadata
        # Publish the host entry last: additions are present before navigation.
        for name in sorted(files,key=lambda n:3 if n==host+'index.html' else 0 if n.endswith('sv08-printer/redirect.js') else 1 if n.endswith('sv08-printer/index.html') else 2):
            if name in expected and expected[name]==after[name]:continue
            check_snapshot(root,snapshot)
            path=safe(root,name);metadata=after[name];temporary=path.with_name(path.name+'.integration-tmp')
            try:
                with temporary.open('xb') as stream:stream.write(files[name]);stream.flush();os.fsync(stream.fileno())
                temporary.chmod(metadata['mode']);os.chown(temporary,metadata['uid'],metadata['gid']);check_snapshot(root,snapshot,temporary);os.replace(temporary,path);snapshot[name]=metadata
            finally:
                if temporary.exists():temporary.unlink()
        check_snapshot(root,snapshot)
    return report


def restore(root, report, interrupted=False):
    with root_lock(root):
        return _restore(root, report, interrupted)


def _restore(root, report, interrupted=False):
    root=Path(root).absolute()
    # Check every afterimage and unchanged preimage before touching anything.
    expected=dict(report['before']);expected.update(report['after']);expected.update(report['new_directories'])
    if interrupted:
        # Only exact recorded preimages/afterimages are recoverable; no guessing.
        checked={}
        for name,metadata in expected.items():
            path=safe(root,name)
            if not path.exists():
                if name in report['before']:raise ValueError('Missing preimage during restoration')
                continue
            actual=inventory(root,[name])[name]
            if actual!=metadata and actual!=report['before'].get(name):raise ValueError('Afterimage changed; restoration refused')
            checked[name]=actual
    elif inventory(root,expected)!=expected:raise ValueError('Afterimage changed; restoration refused')
    for name in report['new_directories']:
        path=safe(root,name)
        if path.exists() and any(str(child.relative_to(root)) not in expected for child in path.rglob('*')):raise ValueError('Afterimage directory contents changed; restoration refused')
    for name in report['originals']:
        temporary=safe(root,name).with_name(Path(name).name+'.restore-tmp')
        if temporary.exists() or temporary.is_symlink():raise ValueError('Unexpected restoration temporary')
    snapshot={name:checked.get(name) for name in expected} if interrupted else dict(expected)
    # Revert navigation first, then its dependencies. Originals remain in report.
    names=sorted(report['after'],key=lambda n:0 if n.endswith('sv08-host/index.html') else 1)
    for name in names:
        check_snapshot(root,snapshot)
        path=safe(root,name)
        if name in report['originals']:
            if sha(path.read_bytes())==report['before'][name]['sha256']:continue
            metadata=report['before'][name];temporary=path.with_name(path.name+'.restore-tmp')
            try:
                with temporary.open('xb') as stream:stream.write(bytes.fromhex(report['originals'][name]));stream.flush();os.fsync(stream.fileno())
                temporary.chmod(metadata['mode']);os.chown(temporary,metadata['uid'],metadata['gid']);check_snapshot(root,snapshot,temporary);os.replace(temporary,path);snapshot[name]=metadata
            finally:
                if temporary.exists():temporary.unlink()
        elif path.exists():path.unlink();snapshot[name]=None
    for name in sorted(report['new_directories'],key=lambda n:len(Path(n).parts),reverse=True):
        check_snapshot(root,snapshot)
        path=safe(root,name)
        if path.exists():path.rmdir();snapshot[name]=None
    check_snapshot(root,snapshot)
    return {'restored':True,'activated':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--preimages',type=Path,required=True)
    parser.add_argument('--validation-dictionary',type=Path)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--fresh',action='store_true');args=parser.parse_args()
    print(json.dumps(stage(args.root,json.loads(args.preimages.read_text()),args.execute,args.fresh,args.validation_dictionary),indent=2))
