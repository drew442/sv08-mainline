#!/usr/bin/env python3
"""Exact additive printer package staging into a disposable root. No activation.

Overlay requires a caller-supplied complete file/mode inventory of the reviewed
host closure. Restoration checks every afterimage before restoring one host file.
"""
import argparse
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
        if not path.is_file():raise ValueError('Missing exact closure file: '+name)
        st=path.stat()
        if st.st_nlink!=1:raise ValueError('Unexpected staging hardlink')
        result[name]={'sha256':sha(path.read_bytes()),'mode':stat.S_IMODE(st.st_mode)}
    return result


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
    files=payload()
    for name in files:
        p=safe(root,name)
        if p.exists():raise ValueError('Existing printer payload conflict')
    report={'format_version':1,'activated':False,'before':expected,'host_before':before.decode(),'host_after':sha(after),'new':{n:{'sha256':sha(raw),'mode':0o644} for n,raw in files.items()},'payload_bytes':sum(map(len,files.values()))+len(after)-len(before),'feature_storage_limit':4*1024*1024}
    if execute:
        # All preconditions checked before the first mutation. Disposable staging
        # may be discarded on interruption; installation remains coordinator-owned.
        for name,raw in files.items():
            p=safe(root,name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o644)
        safe(root,host).write_bytes(after)
    return report


def restore(root, report):
    root=Path(root).absolute();host='usr/share/cockpit/sv08-host/index.html'
    if sha(safe(root,host).read_bytes())!=report['host_after'] or inventory(root,report['new'])!=report['new']:
        raise ValueError('Afterimage changed; restoration refused')
    expected=dict(report['before']);expected.pop(host)
    if inventory(root,expected)!=expected:raise ValueError('Existing closure changed; restoration refused')
    safe(root,host).write_text(report['host_before']);safe(root,host).chmod(report['before'][host]['mode'])
    for name in report['new']:safe(root,name).unlink()
    for relative in ('usr/share/cockpit/sv08-printer','usr/share/sv08/printer'):
        target=safe(root,relative)
        for p in sorted(target.rglob('*'),reverse=True):
            if p.is_dir():p.rmdir()
        target.rmdir()
    return {'restored':True,'activated':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--preimages',type=Path,required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--fresh',action='store_true');args=parser.parse_args()
    print(json.dumps(stage(args.root,json.loads(args.preimages.read_text()),args.execute,args.fresh),indent=2))
