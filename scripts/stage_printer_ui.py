#!/usr/bin/env python3
"""Exact additive printer package staging into a disposable root. No activation.

Overlay requires a caller-supplied complete file/mode inventory of the reviewed
host closure. Restoration checks every afterimage before restoring one host file.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

REPO=Path(__file__).resolve().parents[1]
NAV=b'<a href="../sv08-printer/index.html">Printer hardware</a>'
ANCHOR=b'<p class="eyebrow">YOUR PRINTER</p>'


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


def payload():
    result={}
    for directory,target in [('ui/printer','usr/share/cockpit/sv08-printer'),('catalog/printer','usr/share/sv08/printer')]:
        for p in sorted((REPO/directory).rglob('*')):
            if p.is_file():result[target+'/'+str(p.relative_to(REPO/directory))]=p.read_bytes()
    for p in sorted((REPO/'runtime').glob('sv08_printer_*.py')):result['usr/lib/sv08/'+p.name]=p.read_bytes()
    return result


def stage(root, expected, execute=False, fresh=False):
    root=Path(root).absolute()
    if not root.is_dir() or root.is_symlink():raise ValueError('Expected disposable root')
    required={'usr/lib/sv08/sv08_state.py','usr/lib/sv08/admin-context.json','etc/cockpit/cockpit.conf','usr/share/cockpit/sv08-host/index.html','usr/share/cockpit/sv08-host/session.js','usr/share/cockpit/sv08-host/app.js','usr/share/cockpit/sv08-host/manifest.json'}
    if not isinstance(expected,dict) or not required<=set(expected):raise ValueError('Exact reviewed closure inventory is required')
    files=payload()
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
    if any(p.name not in {'base1','static','branding','issue','motd','sv08-host'} for p in packages.iterdir()):raise ValueError('Unexpected package inventory')
    host='usr/share/cockpit/sv08-host/index.html';before=safe(root,host).read_bytes()
    if fresh:
        if before!=(REPO/'ui/host/index.html').read_bytes() or (root/'usr/lib/sv08/sv08_state.py').read_bytes()!=(REPO/'runtime/sv08_state.py').read_bytes():
            raise ValueError('Fresh staging requires matching current host/core inputs')
        after=before
    else:
        if before.count(ANCHOR)!=1 or NAV in before:raise ValueError('Unexpected host navigation preimage')
        after=before.replace(ANCHOR,ANCHOR+b'\n'+NAV,1)
    for name in files:
        p=safe(root,name)
        if p.exists():raise ValueError('Existing printer payload conflict')
    owner=safe(root,'usr/lib/sv08/sv08_state.py').stat()
    directories={}
    for name in files:
        parent=Path(name).parent
        while str(parent)!='.' and not safe(root,str(parent)).exists():
            directories[str(parent)]=dict(kind='directory',mode=0o755,uid=owner.st_uid,gid=owner.st_gid);parent=parent.parent
    report={'format_version':2,'activated':False,'before':expected,'host_before':before.decode(),'host_after':sha(after),'new':{n:{'kind':'file','sha256':sha(raw),'mode':0o644,'uid':owner.st_uid,'gid':owner.st_gid} for n,raw in files.items()},'new_directories':directories,'dependency_closure':closure,'payload_bytes':sum(map(len,files.values()))+len(after)-len(before),'feature_storage_limit':4*1024*1024,'runtime_dependencies':['existing Python3 standard library','selected Cockpit337 base1','existing sudo privileged bridge']}
    if execute:
        # All preconditions checked before the first mutation. Disposable staging
        # may be discarded on interruption; installation remains coordinator-owned.
        for name,metadata in sorted(directories.items(),key=lambda item:len(Path(item[0]).parts)):
            p=safe(root,name);p.mkdir();p.chmod(metadata['mode'])
            if (p.stat().st_uid,p.stat().st_gid)!=(metadata['uid'],metadata['gid']):os.chown(p,metadata['uid'],metadata['gid'])
        for name,raw in files.items():
            p=safe(root,name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o644)
            if (p.stat().st_uid,p.stat().st_gid)!=(owner.st_uid,owner.st_gid):os.chown(p,owner.st_uid,owner.st_gid)
        safe(root,host).write_bytes(after)
    return report


def restore(root, report):
    root=Path(root).absolute();host='usr/share/cockpit/sv08-host/index.html'
    host_metadata=dict(report['before'][host],sha256=report['host_after'])
    if inventory(root,[host])!={host:host_metadata} or inventory(root,report['new'])!=report['new'] or inventory(root,report['new_directories'])!=report['new_directories']:
        raise ValueError('Afterimage changed; restoration refused')
    expected=dict(report['before']);expected.pop(host)
    if inventory(root,expected)!=expected:raise ValueError('Existing closure changed; restoration refused')
    safe(root,host).write_text(report['host_before']);safe(root,host).chmod(report['before'][host]['mode'])
    for name in report['new']:safe(root,name).unlink()
    for relative in sorted(report['new_directories'],key=lambda name:len(Path(name).parts),reverse=True):safe(root,relative).rmdir()
    return {'restored':True,'activated':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--preimages',type=Path,required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--fresh',action='store_true');args=parser.parse_args()
    print(json.dumps(stage(args.root,json.loads(args.preimages.read_text()),args.execute,args.fresh),indent=2))
