#!/usr/bin/env python3
"""Explicit one-shot NFS image and signed-claim service for H616 commissioning.

Run as root after preparing a reviewed job. A started job is never restarted or
rearmed by this command, even if service startup or acknowledgement fails.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import time

from scripts.prepare_h616_reimage_job import (LOCAL, build_claim_server,
                                               durable_file, fsync_dir, sha256_file)


def safe_path(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    if (not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)) or
            '..' in path.parts or any(part.is_symlink() for part in (path, *path.parents))):
        raise ValueError('Simple absolute non-symlink path required')
    return path


def ganesha_config(*, export_dir: Path, pseudo: str, bind: str,
                   printer_ip: str, recovery_dir: Path) -> str:
    """One read-only VFS export; all unmatched clients are denied."""
    export_dir = safe_path(export_dir)
    recovery_dir = safe_path(recovery_dir)
    bind = str(ipaddress.IPv4Address(bind))
    printer_ip = str(ipaddress.IPv4Address(printer_ip))
    if (not re.fullmatch(r'/[A-Za-z0-9_./-]+', pseudo) or
            '..' in pseudo.split('/') or bind == printer_ip or
            ipaddress.IPv4Address(bind).is_loopback or
            ipaddress.IPv4Address(printer_ip).is_loopback):
        raise ValueError('Unsafe NFS listener, client or export')
    return f'''NFS_CORE_PARAM {{ Protocols = 3; Bind_Addr = {bind}; mount_path_pseudo = true; }}
NFSV4 {{ IdmapConf = "{recovery_dir.parent / 'idmap.conf'}"; UseGetpwnam = true; Graceless = true; RecoveryRoot = "{recovery_dir}"; }}
EXPORT {{
  Export_Id = 1;
  Path = "{export_dir}";
  Pseudo = "{pseudo}";
  Access_Type = NONE;
  Squash = Root_Squash;
  SecType = sys;
  Protocols = 3;
  Transports = TCP;
  FSAL {{ Name = VFS; }}
  CLIENT {{ Clients = {printer_ip}; Access_Type = RO; Squash = Root_Squash; }}
}}
'''


def port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=.2):
            return True
    except OSError:
        return False


def serve(*, state_dir: Path, image: Path, job_verification_key: Path,
          receipt_signing_key: Path, export_dir: Path, printer_ip: str,
          rpcbind: Path, ganesha: Path, execute: bool = False) -> dict:
    state_dir = safe_path(state_dir)
    export_dir = safe_path(export_dir)
    image = safe_path(image)
    rpcbind, ganesha = safe_path(rpcbind), safe_path(ganesha)
    receipt = json.loads((state_dir / 'state.json').read_bytes())
    bind, pseudo = receipt['source_server'], receipt['source_export']
    if not state_dir.is_relative_to(LOCAL) or not export_dir.parent.is_dir():
        raise ValueError('State or export directory is not in its assigned place')
    if export_dir.exists() or port_open(bind, 111) or port_open(bind, 2049):
        raise ValueError('Export destination or NFS service already exists')
    if (not stat.S_ISREG(image.lstat().st_mode) or
            stat.S_IMODE(image.stat().st_mode) & 0o004 == 0):
        raise ValueError('Read-only NFS source must be world-readable')
    if stat.S_IMODE(image.parent.stat().st_mode) & 0o077:
        raise ValueError('World-readable image requires a private 0700 parent directory')
    for executable in (rpcbind, ganesha):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError('Pinned NFS executable unavailable')
    config = ganesha_config(export_dir=export_dir, pseudo=pseudo, bind=bind,
                            printer_ip=printer_ip, recovery_dir=state_dir / 'ganesha-recovery')
    report = {'status': 'inspection-only' if not execute else 'serving-once',
              'state_dir': str(state_dir), 'export_dir': str(export_dir),
              'image_sha256': receipt['image_sha256'], 'bind': bind,
              'printer_ip': printer_ip, 'claim_port': receipt['claim_port'],
              'automatic_rearm': False,
              'source_and_claim_verified': bool(execute),
              'rpcbind_sha256': sha256_file(rpcbind),
              'ganesha_sha256': sha256_file(ganesha)}
    if not execute:
        return report
    if os.geteuid() != 0:
        raise PermissionError('Explicit service launch requires root')
    if (state_dir / 'serve-start.json').exists():
        raise ValueError('Service was already started; never retry or rearm')
    # Full hash and durable claim are checked before NFS/HTTP listeners start.
    claim_server = build_claim_server(state_dir=state_dir, image_path=image,
                                      job_verification_key=job_verification_key,
                                      receipt_signing_key=receipt_signing_key,
                                      bind=bind)
    durable_file(state_dir / 'serve-start.json',
                 (json.dumps(report, sort_keys=True) + '\n').encode())
    fsync_dir(state_dir)
    children = []
    try:
        export_dir.mkdir(mode=0o755)
        os.link(image, export_dir / 'image.bin', follow_symlinks=False)
        (state_dir / 'ganesha-recovery').mkdir(mode=0o700)
        durable_file(state_dir / 'idmap.conf', b'[General]\nDomain = localdomain\n')
        config_path = state_dir / 'ganesha.conf'
        durable_file(config_path, config.encode())
        fsync_dir(state_dir)
        children.append(subprocess.Popen([str(rpcbind), '-f', '-s'],
                                         stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL))
        children.append(subprocess.Popen([str(ganesha), '-F', '-f', str(config_path),
                                          '-L', str(state_dir / 'ganesha.log'),
                                          '-p', str(state_dir / 'ganesha.pid')],
                                         stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL))
        for _ in range(100):
            if any(child.poll() is not None for child in children):
                raise RuntimeError('NFS service exited before readiness')
            if port_open(bind, 2049):
                break
            time.sleep(.1)
        else:
            raise TimeoutError('NFS service did not become ready')
        claim_server.timeout = .2
        try:
            while True:
                if any(child.poll() is not None for child in children):
                    raise RuntimeError('NFS service exited during job')
                # A consumed claim is only permission to start the transfer;
                # keep NFS available until an operator observes the guest's
                # terminal result and stops this foreground service.
                if (int(time.time()) >= receipt['expires_unix'] and
                        not (state_dir / 'claim/claim.json').exists()):
                    break
                claim_server.handle_request()
        except KeyboardInterrupt:
            pass
    finally:
        claim_server.server_close()
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        try:
            (export_dir / 'image.bin').unlink()
            export_dir.rmdir()
        except OSError:
            pass  # Retain uncertain state for manual inspection.
        terminal = {'status': 'claim-consumed' if (state_dir / 'claim/claim.json').exists()
                    else 'stopped-unclaimed', 'automatic_rearm': False}
        durable_file(state_dir / 'serve-terminal.json',
                     (json.dumps(terminal, sort_keys=True) + '\n').encode())
        fsync_dir(state_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state-dir', 'image', 'job-verification-key', 'receipt-signing-key',
                 'export-dir', 'rpcbind', 'ganesha'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--printer-ip', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    report = serve(state_dir=args.state_dir, image=args.image,
                   job_verification_key=args.job_verification_key,
                   receipt_signing_key=args.receipt_signing_key,
                   export_dir=args.export_dir, printer_ip=args.printer_ip,
                   rpcbind=args.rpcbind, ganesha=args.ganesha,
                   execute=args.execute)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
