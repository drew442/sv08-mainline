"""Offline construction phase, no candidate runtime or hardware access."""
import hashlib,json, subprocess, os, sys
from pathlib import Path

def main():
    def call(*args): subprocess.run(args, check=True, timeout=120)
    call('mount','-t','proc','proc','/proc')
    call('mount','-t','sysfs','sysfs','/sys')
    call('mount','-t','tmpfs','-o','mode=755','tmpfs','/run')
    call('mount','-t','tmpfs','-o','size=32m,mode=755','tmpfs','/var/log')
    Path('/usr/sbin/policy-rc.d').write_text('#!/bin/sh\nexit 101\n')
    Path('/usr/sbin/policy-rc.d').chmod(0o755)
    for unit in ('sv08-klipper','sv08-moonraker','klipper','moonraker','octoprint','ssh','NetworkManager','systemd-networkd','cockpit'):
        path=Path('/etc/systemd/system')/(unit+'.service')
        path.unlink(missing_ok=True); path.symlink_to('/dev/null')
    package_receipt=json.loads(Path('/input/packages.json').read_text())
    packages=[]
    for entry in package_receipt['packages']:
        assert Path(entry['filename']).name==entry['filename']
        path=Path('/input')/entry['filename']
        assert hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==entry['sha256']
        packages.append(str(path))
    call('dpkg','-i',*packages)
    versions=subprocess.check_output(['dpkg-query','-W','-f=${Package} ${Version} ${db:Status-Abbrev}\\n','rauc','sv08-klipper'],text=True)
    assert 'rauc 1.15.2-0sv08.1 ii' in versions and 'sv08-klipper 0.0+gitf0892d82-1 ii' in versions
    assert subprocess.check_output(['/usr/bin/rauc','--version'],text=True).strip()=='rauc 1.15.2'
    stamp=json.loads(Path('/usr/share/doc/sv08-klipper/release.json').read_text())
    assert stamp['source_commit']=='f0892d82b0f1c1228454f09eb508eddde2250f4b'
    print('CONSTRUCTION_PACKAGE_RESULT '+json.dumps({'versions':versions,'klipper_source_commit':stamp['source_commit'],'network':False}),flush=True)
    call('sync')
    print('CONSTRUCTION_PASS',flush=True)
    call('poweroff','-f')

def boot():
    def call(*args):subprocess.run(args,check=True,timeout=30)
    for kind,path in [('proc','/proc'),('sysfs','/sys')]:
        subprocess.run(['mount','-t',kind,kind,path],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    assert 'sv08.test=rauc-backend' in Path('/proc/cmdline').read_text().split()
    assert Path('/sys/block/vda/serial').read_text().strip()=='SV08-QEMU-DISPOSABLE'
    call('mount','-t','tmpfs','-o','mode=755','tmpfs','/run')
    call('mount','/dev/disk/by-partuuid/4773f966-0678-4cf5-bb83-8ee6fb11d8eb','/data')
    sys.path.insert(0,'/usr/lib/sv08')
    from sv08_state import Store
    from sv08_boot import initialize_identity
    store=Store('/data/sv08');store.initialize();initialize_identity(store.root)
    call('mount','--bind','/data/sv08/system/machine-id','/etc/machine-id')
    call('mount','--bind','/data/sv08/system/hostname','/etc/hostname')
    call('mount','--bind','/data/sv08/system/hosts','/etc/hosts')
    os.execv('/lib/systemd/systemd',['/lib/systemd/systemd','--unit=fixture.target'])

if __name__=='__main__':
    try:
        if '--boot' in sys.argv: boot()
        else: main()
    except BaseException as exc:
        print('CONSTRUCTION_FAILURE '+repr(exc),flush=True)
        subprocess.run(['poweroff','-f'],timeout=10)
        raise
