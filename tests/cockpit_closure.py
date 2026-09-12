#!/usr/bin/env python3
"""Derive selected Cockpit Depends/Pre-Depends from local pinned APT metadata.

Read only: native python3-apt parses dependencies, dpkg-deb reads archive controls.
Includes every installed satisfying alternative/provider, not Recommends/Suggests.
No package install, resolver update, service launch or guest access.
"""
import argparse
import apt_pkg, pathlib, json, subprocess, hashlib
apt_pkg.init_system()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',type=pathlib.Path,required=True)
parser.add_argument('--intake',type=pathlib.Path,required=True)
parser.add_argument('--output',type=pathlib.Path,required=True)
args=parser.parse_args()
baseline=args.baseline; intake=args.intake
lock=json.loads((pathlib.Path(__file__).resolve().parents[1]/'configs/host-os/cockpit-packages.json').read_text())
def paragraphs(path):
    with open(path) as f:
        for p in apt_pkg.TagFile(f):
            yield dict(p)
installed={p['Package']:p for p in paragraphs(baseline/'var/lib/dpkg/status') if p.get('Status')=='install ok installed'}
for item in lock['delta']:
    assert hashlib.sha256((intake/item['file']).read_bytes()).hexdigest()==item['sha256'], 'Archive hash mismatch'
    s=subprocess.check_output(['dpkg-deb','-f',str(intake/item['file'])],text=True)
    p=dict(apt_pkg.TagSection(s)); installed[p['Package']]=p
metadata={}
indexes=[]
for path in sorted((baseline/'var/lib/apt/lists').glob('*_Packages')):
    archive='debian-security' if '_debian-security_' in path.name else 'debian'
    indexes.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    for p in paragraphs(path):
        key=(p['Package'],p['Version'],p['Architecture'])
        metadata.setdefault(key,[]).append({'url':f'https://snapshot.debian.org/archive/{archive}/20260901T000000Z/'+p['Filename'],'sha256':p['SHA256'],'bytes':int(p['Size'])})
providers={}
for name,p in installed.items():
    for group in apt_pkg.parse_depends(p.get('Provides',''),False):
        for n,v,op in group:
            providers.setdefault(n,[]).append((name,v))
def satisfies(actual,wanted,op):
    return not op or apt_pkg.check_dep(actual,op,wanted)
queue=['cockpit-bridge','cockpit-ws','sudo']; result={}; edges=[]; unresolved=[]
while queue:
    name=queue.pop(0)
    if name in result: continue
    p=installed[name]; key=(name,p['Version'],p['Architecture'])
    result[name]={'package':name,'version':p['Version'],'architecture':p['Architecture'],'archives':metadata.get(key,[])}
    for field in ['Pre-Depends','Depends']:
        for group in apt_pkg.parse_depends(p.get(field,''),False):
            selected=[]
            for dep,wanted,op in group:
                dep=dep.split(':')[0]
                if dep in installed and satisfies(installed[dep]['Version'],wanted,op): selected.append(dep)
                for provider,version in providers.get(dep,[]):
                    if not op or version and satisfies(version,wanted,op): selected.append(provider)
            selected=sorted(set(selected))
            edges.append({'from':name,'field':field,'alternatives':[list(x) for x in group],'installed_satisfiers':selected})
            if not selected: unresolved.append(edges[-1])
            queue.extend(selected)
out={'format_version':1,'snapshot':'20260901T000000Z','roots':['cockpit-bridge','cockpit-ws','sudo'],'method':'Recursive Depends/Pre-Depends closure over exact baseline installed status plus nine pinned delta deb controls; include every installed satisfying alternative/provider, exclude Recommends/Suggests. Archive metadata matched by exact name/version/architecture against existing snapshot indexes. No package installation or guest mutation.','indexes':indexes,'packages':sorted(result.values(),key=lambda x:x['package']),'edges':edges,'unresolved':unresolved}
assert not unresolved,unresolved
assert all(p['archives'] for p in out['packages']),[p for p in out['packages'] if not p['archives']]
path=args.output
with path.open('x') as stream: stream.write(json.dumps(out,indent=2)+'\n')
print(json.dumps({'path':str(path),'packages':len(result),'edges':len(edges),'unresolved':len(unresolved),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
