#!/usr/bin/env python3
"""Rebuild the pinned streaming-form-data wheel with canonical debug paths.

Uses supported compiler/pip options, with no source patch. Default inspection;
only a prepared compiler root below build/ is accepted. Retire when the selected
upstream wheel or distro package supplies the required reproducible ARM64 build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from prepare_host_os import REPO


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler-root',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--build-venv',default='/tmp/build-venv')
    p.add_argument('--work-name',required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    c=json.loads((REPO/'configs/host/compiled-source-wheels.json').read_text())['streaming_form_data']
    root=a.compiler_root.resolve()
    if not root.is_relative_to(REPO/'build') or root==REPO/'build':raise ValueError('Use a prepared build-directory compiler root')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',a.work_name):raise ValueError('Invalid fresh work name')
    if not a.build_venv.startswith('/tmp/') or '..' in Path(a.build_venv).parts:raise ValueError('Use a private compiler venv under /tmp')
    prefix='/tmp/'+a.work_name;work=root/prefix.lstrip('/')
    if work.exists() or work.is_symlink():raise ValueError('Use a fresh source/build directory')
    if sha(a.source)!=c['source_sha256']:raise ValueError('Source hash mismatch')
    print(json.dumps(dict(execute=a.execute,compiler_root=str(root),work=str(work),source_sha256=c['source_sha256'])))
    if not a.execute:return
    if os.geteuid()!=0:raise ValueError('Execution requires root for the isolated compiler chroot')
    python=a.build_venv+'/bin/python'
    query='import sys,sysconfig,json,importlib.metadata as m; print(json.dumps([list(sys.version_info[:3]),m.version("setuptools"),sysconfig.get_config_var("CFLAGS")]))'
    versions=json.loads(subprocess.check_output(['chroot',str(root),python,'-c',query],text=True))
    if versions!=[[3,13,5],c['setuptools'],c['python_cflags']]:raise ValueError('Unreviewed Python/backend/compiler flags')
    compiler=subprocess.check_output(['chroot',str(root),'dpkg-query','-W','-f=${Version}','gcc-14'],text=True)
    if compiler!='14.2.0-19':raise ValueError('Unreviewed compiler package')
    work.mkdir()
    with tarfile.open(a.source) as tar:tar.extractall(work,filter='data')
    (work/'streaming_form_data-2.1.0').rename(work/c['source_directory_basename'])
    flags=c['python_cflags']+' '+' '.join(x.format(work=prefix,venv=a.build_venv) for x in c['additional_cflags'])
    subprocess.run(['chroot',str(root),'/usr/bin/env','PATH='+a.build_venv+'/bin:/usr/bin:/bin',
        'SOURCE_DATE_EPOCH='+str(c['source_date_epoch']),'PYTHONHASHSEED='+c['python_hash_seed'],
        'CFLAGS='+flags,python,'-m','pip','wheel','--no-index','--no-cache-dir',
        '--no-build-isolation','--no-deps','--wheel-dir',prefix+'/wheels',prefix+'/'+c['source_directory_basename']],check=True)
    wheel=work/'wheels'/c['filename'];actual=sha(wheel)
    report=dict(filename=wheel.name,sha256=actual,expected_sha256=c['sha256'],
        matches_recorded_build=actual==c['sha256'],compiler=compiler,python_backend_flags=versions)
    (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if actual!=c['sha256']:raise ValueError('Wheel differs from the reviewed reproducible output; retain for investigation')


if __name__=='__main__':main()
