#!/usr/bin/env python3
"""Create an isolated opt-in overlay; never install, enable units or touch devices.

Uses exact pre-TLS installed sources plus the accepted TLS commit, without current
runtime/UI refresh. The manifest is input to coordinator-owned installation review.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
BASE = '6064628ff06261a604aa13c52e17407b33f9f503'
TLS = '8c6f24f5a565cd08e43001414f643f55d5b1bb8b'
DEPENDENCY_REVISION = '1d1855719169f024b3d36f7e9bbe1fb4d5f28894'
MAX_PAYLOAD = 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(revision, path):
    return subprocess.check_output(['git', '-C', str(REPO), 'show', revision + ':' + path], timeout=3)


def bounded_sha(path):
    if path.stat().st_size > 65536:
        raise ValueError('Oversized installed preflight input')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Linked source/output path')
    return path


def historical_preimage(installed, relative, repo_path):
    path = safe(installed / relative)
    expected = source(BASE, repo_path)
    if not path.is_file() or path.stat().st_size > 64 * 1024 or path.read_bytes() != expected:
        raise ValueError('Installed historical preimage differs/missing: ' + relative)
    return expected


def dependency_closure():
    pending = ['sv08_commissioning_health']
    seen = {}
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        data = ((REPO / 'runtime' / (name + '.py')).read_bytes() if name == 'sv08_commissioning_health'
                else source(DEPENDENCY_REVISION if name == 'sv08_rauc_bootloader' else BASE, 'runtime/' + name + '.py'))
        seen[name] = data
        for node in ast.walk(ast.parse(data)):
            modules = [node.module] if isinstance(node, ast.ImportFrom) else ([a.name for a in node.names] if isinstance(node, ast.Import) else [])
            pending.extend(m for m in modules if m and m.startswith('sv08_') and m not in seen)
    return seen


def stage(installed, target_config, output=None, execute=False, deployment_preimages=None):
    installed = safe(installed)
    if not installed.is_dir():
        raise ValueError('Non-secret installed-source directory is required')
    sys.path.insert(0, str(REPO / 'runtime'))
    from sv08_commissioning_health import validate_config
    config = validate_config(target_config)
    payload, preimages = {}, {}
    for name in ('sv08_state', 'sv08_boot'):
        rel = 'usr/lib/sv08/' + name + '.py'
        historical_preimage(installed, rel, 'runtime/' + name + '.py')
        before, after = source(BASE, 'runtime/' + name + '.py'), source(TLS, 'runtime/' + name + '.py')
        mode = 0o755 if name == 'sv08_state' else 0o644
        payload[rel] = (after, mode)
        preimages[rel] = dict(kind='file', sha256=sha(before), mode=mode)
    # Branding is applied to old CSS bytes using the exact same palette delta;
    # old app.js, manifest, session/upload helpers and protocol remain untouched.
    old_css = historical_preimage(installed, 'usr/share/cockpit/sv08-host/style.css', 'ui/host/style.css')
    base_css = source(BASE, 'ui/host/style.css')
    for filename in ('app.js', 'manifest.json', 'index.html'):
        historical_preimage(installed, 'usr/share/cockpit/sv08-host/' + filename, 'ui/host/' + filename)
    old_html = source(BASE, 'ui/host/index.html')
    themed_html = old_html.replace(b'<title>SV08 \xc2\xb7 Host administration</title>', b'<title>SV08 Mainline \xc2\xb7 Host administration</title>')
    for name, before, after in [('style.css', old_css, (REPO / 'ui/host/style.css').read_bytes()),
                                ('index.html', old_html, themed_html)]:
        rel = 'usr/share/cockpit/sv08-host/' + name
        payload[rel] = (after, 0o644)
        preimages[rel] = dict(kind='file', sha256=sha(before), mode=0o644)
    for path in sorted((REPO / 'configs/host-os/cockpit-branding').iterdir()):
        rel = 'usr/share/cockpit/branding/debian/' + path.name
        payload[rel] = (path.read_bytes(), 0o644)
        # Stock branding was not captured. Installation must bind exact existing
        # hash/mode or observed absence in the coordinator's reviewed manifest.
        capture = (deployment_preimages or {}).get('/' + rel)
        if capture is None:
            raise ValueError('Exact deployment branding preimage is required: ' + rel)
        if capture['kind'] == 'file':
            preimages[rel] = {key: capture[key] for key in ('kind', 'sha256', 'mode')}
        elif capture['kind'] == 'absent':
            preimages[rel] = dict(kind='absent')
        else:
            raise ValueError('Unsupported deployment branding preimage')
    payload['usr/lib/sv08/sv08_commissioning_health.py'] = ((REPO / 'runtime/sv08_commissioning_health.py').read_bytes(), 0o644)
    bootloader = source(DEPENDENCY_REVISION, 'runtime/sv08_rauc_bootloader.py')
    if bootloader != (REPO / 'runtime/sv08_rauc_bootloader.py').read_bytes():
        raise ValueError('Reconcile bootloader source before staging unchanged dependency')
    payload['usr/lib/sv08/sv08_rauc_bootloader.py'] = (bootloader, 0o644)
    payload['usr/lib/systemd/system/sv08-commissioning-health.service'] = ((REPO / 'configs/host-os/commissioning/sv08-commissioning-health.service').read_bytes(), 0o644)
    payload['usr/lib/sv08/admin-context.json'] = (b'{"format_version":1,"context":"host"}\n', 0o644)
    payload['etc/sv08/commissioning-target.json'] = ((json.dumps(config, sort_keys=True, indent=2)+'\n').encode(), 0o600)
    payload['etc/sv08/commissioning-fw_env.config'] = (''.join(f"{config['disk']['path']} {offset:#x} 0x10000\n" for offset in (0x400000, 0x800000)).encode(), 0o600)
    if sha(payload['etc/sv08/commissioning-fw_env.config'][0]) != config['fw_config_sha256']:
        raise ValueError('Private config/map hash differs')
    for rel in payload:
        preimages.setdefault(rel, dict(kind='absent'))
    unchanged = {}
    for name in ('app.js', 'manifest.json'):
        rel = 'usr/share/cockpit/sv08-host/' + name
        unchanged[rel] = dict(sha256=sha(source(BASE, 'ui/host/' + name)), mode=0o644)
    shell = b'[WebService]\nShell=/sv08-host/index.html\n'
    shell_path = safe(installed / 'etc/cockpit/cockpit.conf')
    if not shell_path.is_file() or shell_path.stat().st_size != len(shell) or shell_path.read_bytes() != shell:
        raise ValueError('Installed fixed Cockpit shell config differs')
    unchanged['etc/cockpit/cockpit.conf'] = dict(sha256=sha(shell), mode=0o644)
    closure = {}
    for name, data in dependency_closure().items():
        rel = '/usr/lib/sv08/' + name + '.py'
        expected = sha(payload[rel[1:]][0] if rel[1:] in payload else data)
        if name not in ('sv08_commissioning_health', 'sv08_rauc_bootloader'):
            candidate = installed / rel[1:]
            historical_preimage(installed, rel[1:], 'runtime/' + name + '.py')
        closure[rel] = expected
    if config['dependencies'] != closure:
        raise ValueError('Target dependency hash closure differs (derive with dependency_closure)')
    # Never read identity keys, passwords or certificate content. This is a link
    # inventory only; coordinator creates the private 0700 data directory via the
    # accepted Store.initialize/prepare_permissions before execution.
    links = {'etc/cockpit/ws-certs.d': '/data/sv08/system/cockpit/ws-certs.d'}
    preimages['etc/cockpit/ws-certs.d'] = dict(kind='empty-directory', mode=0o755)
    payload_bytes = sum(len(data) for data, _ in payload.values())
    if payload_bytes > MAX_PAYLOAD:
        raise ValueError('Overlay payload exceeds 1 MiB bound')
    preserved_bytes = sum(len(source(BASE, 'runtime/'+n+'.py')) for n in ('sv08_state', 'sv08_boot')) + len(old_css) + len(old_html)
    preserved_bytes += sum(value['bytes'] for key, value in (deployment_preimages or {}).items()
                           if key.lstrip('/') in payload and key.startswith('/usr/share/cockpit/branding/') and value['kind'] == 'file')
    manifest = dict(format_version=1, base_revision=BASE, tls_revision=TLS, dependency_revision=DEPENDENCY_REVISION, execute=execute,
                    activated=False, deployable=False, payload_bytes=payload_bytes,
                    preserved_beforeimages_bytes_minimum=preserved_bytes,
                    dependency_closure=closure, preimages=preimages, unchanged=unchanged,
                    tool_links={'/usr/bin/fw_setenv': 'fw_printenv',
                                '/usr/lib/aarch64-linux-gnu/libubootenv.so.0': 'libubootenv.so.0.3.5'},
                    files={rel: dict(kind='file', mode=mode, bytes=len(data), sha256=sha(data), uid=0, gid=0)
                           for rel, (data, mode) in sorted(payload.items())},
                    directories={str(parent): dict(kind='directory', mode=0o755)
                                 for rel in [*payload, *links] for parent in Path(rel).parents if str(parent) != '.'},
                    links={rel: dict(kind='symlink', target=target, sha256=sha(target.encode())) for rel, target in links.items()},
                    runtime=dict(deadline_seconds=60, stable_seconds=5, diagnostic_per_boot_bytes=65536,
                                 diagnostic_retained_bytes=1048576, resident_daemon=False),
                    installation_prerequisites=['exact target preimage hashes/modes/links including branding capture',
                         'all unchanged dependencies present and matching closure',
                         'selected tools package/version/executable and complete loader/library hashes agree',
                         'root ro->rw->ro reviewed by coordinator; retain beforeimages and flush/hash all files',
                         'accepted TLS real directory initialization/permissions; do not replace conflicting cert content',
                         'explicit enablement only after independent review; no stage_admin_ui refresh'])
    if output is not None:
        output = safe(output)
        if output.exists():
            raise ValueError('Overlay output must be new')
        fs = os.statvfs(output.parent)
        # Quantify rounded file installation + preserved files + persistent diag
        # reserve, not a changed factory/user-data admission floor.
        rounded = lambda n: ((n+fs.f_frsize-1)//fs.f_frsize)*fs.f_frsize
        needed = sum(rounded(len(data)) for data, _ in payload.values()) + rounded(preserved_bytes) + 1048576
        inodes = len(payload)*2 + len(links) + 32
        manifest['capacity'] = dict(free_bytes=fs.f_bavail*fs.f_frsize, free_inodes=fs.f_favail,
                                   required_bytes_minimum=needed, required_inodes_minimum=inodes,
                                   basis='isolated staging filesystem; coordinator must remeasure actual target and captured branding beforeimages')
        if fs.f_bavail*fs.f_frsize < needed or fs.f_favail < inodes:
            raise ValueError('Insufficient isolated installation/beforeimage capacity')
        if execute:
            output.mkdir(mode=0o700)
            for rel, (data, mode) in sorted(payload.items()):
                path = output / 'rootfs' / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                path.chmod(mode)
            for rel, target in links.items():
                path = output / 'rootfs' / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(target)
            (output / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
    elif execute:
        raise ValueError('Explicit isolated output is required')
    return manifest


def check_target(root, manifest):
    """Read-only preflight on a copied target; no install or writer invocation.

    Coordinator must capture missing stock branding into the candidate manifest
    and run this before a separately reviewed install. Unresolved capture refuses.
    """
    root = safe(root)
    for rel, expected in manifest['preimages'].items():
        path = root / rel
        for parent in path.parents:
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError('Linked target parent: ' + rel)
        kind = expected['kind']
        if kind == 'absent':
            if path.exists() or path.is_symlink():
                raise ValueError('Target conflict: ' + rel)
        elif kind == 'file':
            if (path.is_symlink() or not path.is_file() or
                    bounded_sha(path) != expected['sha256'] or
                    path.stat().st_mode & 0o777 != expected['mode']):
                raise ValueError('Target preimage differs: ' + rel)
        elif kind == 'empty-directory':
            if (path.is_symlink() or not path.is_dir() or any(path.iterdir()) or
                    path.stat().st_mode & 0o777 != expected['mode']):
                raise ValueError('Target certificate directory conflict')
        else:
            raise ValueError('Unresolved coordinator preimage capture: ' + rel)
    for rel, expected in manifest['unchanged'].items():
        path = safe(root / rel)
        if (not path.is_file() or bounded_sha(path) != expected['sha256'] or
                path.stat().st_mode & 0o777 != expected['mode']):
            raise ValueError('Unchanged installed UI/configuration differs: ' + rel)
    for rel, expected in manifest['dependency_closure'].items():
        if rel[1:] in manifest['files']:
            continue
        path = safe(root / rel.lstrip('/'))
        if not path.is_file() or bounded_sha(path) != expected:
            raise ValueError('Missing/incompatible installed dependency: ' + rel)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-source', type=Path, required=True)
    parser.add_argument('--target-config', type=Path, required=True)
    parser.add_argument('--deployment-preimages', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    path = safe(args.target_config)
    if path.stat().st_size > 65536:
        raise ValueError('Oversized target config')
    print(json.dumps(stage(args.installed_source, json.loads(path.read_text()), args.output, args.execute, json.loads(safe(args.deployment_preimages).read_text())), sort_keys=True, indent=2))
