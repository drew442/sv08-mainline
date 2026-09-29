#!/usr/bin/env python3
"""Explicit fixed U-Boot serial routing; defaults to inspection, no reset/power.

Retire this bounded diagnostic controller with supported recovery boot selection.
Requires already configured 115200 8N1 and released receive-only capture.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import select
import stat
import termios
import time
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.sd_boot_route import regular_bytes, sha
from scripts.build_sd_recovery_host import boot_script

SCRIPT_BYTES = 1075
SCRIPT_SHA = 'ce18bf74e3d8ae840bfb90129ba28515ba89cbd2759bc32ecd0418f6987d1ddd'
ROOT = 'deaf981d-7441-428c-bf43-ce40bca6ca65'
ENVELOPE = 'e70601624c206ab0cea69e7ce142e7adeeb0faff13eee5e3fcf545bc08898fa1'
PROMPT = rb'(?:^|\r?\n)=> '
COUNTDOWN = rb'Hit any key to stop autoboot:\s+[0-9]+(?:\s|$)'
CAPTURE_LIMIT = 1024*1024


def verify_script(script, command, composition):
    data = regular_bytes(script)
    record = json.loads(regular_bytes(composition))
    if len(data)!=SCRIPT_BYTES or sha(data)!=SCRIPT_SHA:
        raise ValueError('Unreviewed boot.scr')
    # The script's kernel/initrd/DT checks and fixed args remain unchanged.
    if regular_bytes(command).decode()!=boot_script({name:record['payloads'][name]['sha256'] for name in ('Image','initrd.img','sv08.dtb')},ENVELOPE):
        raise ValueError('Changed payload verification/root/envelope commands')
    return {'script_sha256':SCRIPT_SHA,'script_bytes':SCRIPT_BYTES,'root_partuuid':ROOT,'envelope':ENVELOPE}


class Session:
    def __init__(self, read, write, *, timeout=15, clock=time.monotonic):
        self.read, self.write, self.timeout, self.clock = read, write, timeout, clock
        self.capture = bytearray()
        self.at_prompt = False
        self.verified_script = False

    def wait(self, pattern):
        deadline = self.clock()+self.timeout
        response = bytearray()
        while self.clock()<deadline:
            chunk = self.read(min(0.2,max(0,deadline-self.clock())))
            if chunk:
                response.extend(chunk); self.capture.extend(chunk)
                if len(self.capture)>CAPTURE_LIMIT: raise ValueError('Capture limit')
                if re.search(rb'(?:login:|Password:|(?:^|\n)[^\n]*[$#] )',response):
                    raise ValueError('Linux/unknown shell; stop')
                if re.search(pattern,response): return bytes(response)
        raise TimeoutError('Recognized U-Boot gate timed out; stop')

    def interrupt(self):
        self.wait(COUNTDOWN)
        self.write(b' ')  # Only recognized countdown permits interception.
        self.wait(PROMPT); self.at_prompt = True

    def command(self, command):
        allow = ('mmc dev 0', 'mmc info', 'fatload mmc 0:1 ${scriptaddr} boot.scr',
                 'hash sha256 ${scriptaddr} ${filesize}',
                 'source ${scriptaddr}')
        if command not in allow or not self.at_prompt:
            raise ValueError('Forbidden command or absent U-Boot prompt')
        if command=='source ${scriptaddr}' and not self.verified_script:
            raise ValueError('Source requires verified script result')
        self.at_prompt = False
        self.write(command.encode()+b'\n')
        if command=='source ${scriptaddr}': return b''  # Never retry or TX into Linux.
        response = self.wait(PROMPT)
        self.at_prompt = True
        if command.encode() not in response:
            raise ValueError('Missing exact command echo')
        if re.search(rb'(?:Unknown command|[Ee]rror|[Ff]ail|[Bb]ad |[Uu]nknown)',response):
            raise ValueError('U-Boot command failed; stop')
        return response

    def route(self, route):
        if route not in ('sd','emmc'): raise ValueError('Unknown fixed route')
        if route=='emmc':
            # Standard autoboot, zero bytes sent. Coordinator owns environment review.
            self.wait(COUNTDOWN)
            return
        self.interrupt()
        dev = self.command('mmc dev 0')
        if not re.search(rb'mmc0 is current device',dev): raise ValueError('Unexpected U-Boot MMC mapping')
        info = self.command('mmc info')
        if not re.search(rb'SD version ',info) or re.search(rb'MMC version ',info):
            raise ValueError('MMC0 is not an identified SD card')
        loaded = self.command('fatload mmc 0:1 ${scriptaddr} boot.scr')
        counts = re.findall(rb'(\d+) bytes read',loaded)
        if counts != [str(SCRIPT_BYTES).encode()]: raise ValueError('Unexpected boot.scr byte count')
        hashed = self.command('hash sha256 ${scriptaddr} ${filesize}')
        hashes = re.findall(rb'==>\s*([0-9a-f]{64})(?:\r?\n)',hashed)
        if hashes != [SCRIPT_SHA.encode()]: raise ValueError('Unexpected boot.scr SHA256')
        self.verified_script = True
        self.command('source ${scriptaddr}')


def serial_identity(fd, policy):
    info = os.fstat(fd)
    if not stat.S_ISCHR(info.st_mode) or f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}'!=policy['dev_t']:
        raise ValueError('Serial device identity differs')
    tty = (Path('/sys/dev/char')/policy['dev_t']).resolve()
    if str(tty)!=policy['sysfs_path']: raise ValueError('USB topology differs')
    usb = next((x for x in [tty,*tty.parents] if (x/'idVendor').exists()),None)
    if usb is None or (usb/'idVendor').read_text().strip()!='1a86' or (usb/'idProduct').read_text().strip()!='7523':
        raise ValueError('Not the admitted CH340 bridge')
    attrs = termios.tcgetattr(fd)
    cflag = attrs[2]
    required = termios.CS8|termios.CREAD|termios.CLOCAL
    prohibited = termios.HUPCL|termios.CRTSCTS|termios.PARENB|termios.CSTOPB
    if cflag & (termios.CSIZE|termios.CREAD|termios.CLOCAL)!=required or cflag&prohibited or attrs[4:6]!=[termios.B115200]*2:
        raise ValueError('Require preconfigured 115200 8N1, CLOCAL, no HUPCL/RTSCTS')
    if attrs[3] & (termios.ICANON|termios.ECHO|termios.ISIG) or attrs[1]&termios.OPOST:
        raise ValueError('Require preconfigured raw serial; no attribute changes permitted')
    # Never tcsetattr, TIOCMBIS/BIC, DTR/RTS, reset or power here.


def run(policy, route, script, command, composition, capture, *, apply=False):
    binding = verify_script(script,command,composition)
    if not policy.get('capture_released') or not policy.get('fresh_environment_reviewed') or not policy.get('mmc_mapping_reviewed'):
        raise ValueError('Capture arbitration/MMC/environment review required')
    if not apply: return {'transmit':False,'route':route,**binding}
    if route not in ('sd','emmc'): raise ValueError('Unknown route')
    # Stable lock shared by cooperating capture/controller; kernel TIOCEXCL also
    # prevents subsequent opens. Coordinator releases existing capture first.
    lock = os.open(policy['ownership_lock'],os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    fd = None
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fd = os.open(policy['device'],os.O_RDWR|os.O_NONBLOCK|os.O_NOCTTY|os.O_NOFOLLOW)
        serial_identity(fd,policy)
        for process in Path('/proc').iterdir():
            if not process.name.isdigit(): continue
            try: descriptors=list((process/'fd').iterdir())
            except FileNotFoundError: continue
            except PermissionError: raise ValueError('Cannot inspect existing serial users')
            for descriptor in descriptors:
                if process.name==str(os.getpid()) and descriptor.name==str(fd): continue
                try: other=descriptor.stat()
                except FileNotFoundError: continue
                if stat.S_ISCHR(other.st_mode) and other.st_rdev==os.fstat(fd).st_rdev:
                    raise ValueError('Existing serial capture/controller descriptor')
        fcntl.ioctl(fd,termios.TIOCEXCL)
        def read(timeout):
            return os.read(fd,4096) if select.select([fd],[],[],timeout)[0] else b''
        def write(data):
            serial_identity(fd,policy)
            if os.write(fd,data)!=len(data): raise OSError('Partial serial TX; stop')
        session = Session(read,write)
        try: session.route(route)
        finally:
            out = os.open(capture,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            try:
                if os.write(out,session.capture)!=len(session.capture): raise OSError('Short capture')
                os.fsync(out)
            finally: os.close(out)
        return {'route':route,'transmit':route=='sd',**binding,'capture_sha256':sha(session.capture)}
    finally:
        if fd is not None: os.close(fd)
        os.close(lock)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--route',choices=('sd','emmc'),required=True)
    for name in ('policy','script','command','composition','capture'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    args=vars(p.parse_args()); args['policy']=json.loads(regular_bytes(args['policy']))
    print(json.dumps(run(**args),sort_keys=True,indent=2))


if __name__=='__main__': main()
