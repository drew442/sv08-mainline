#!/usr/bin/env python3
"""Installed, non-fixture entry under Xvfb with isolated invalid trust inputs.

Run sudo unshare --mount --propagation private /usr/bin/python3
tests/recovery_media_entry.py --runtime build/STAGE/rootfs/usr/lib/sv08
No physical media are opened; only private tmpfs /etc and /run are changed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--case', choices=['absent', 'malformed', 'untrusted', 'invalid'])
    args = parser.parse_args()
    if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
        parser.error('Use root in a private mount namespace')
    if args.case:
        sys.path.insert(0, str(args.runtime.resolve()))
        from sv08_recovery_ui import Gtk, GLib, RecoveryWindow, main as installed_main
        result = []
        def inspect():
            for window in Gtk.Window.list_toplevels():
                if isinstance(window, RecoveryWindow) and not window.busy:
                    reason = window.reason.get_text()
                    assert 'User-data export unavailable' in reason, reason
                    expected = {'absent':'No such file', 'malformed':'Expecting',
                                'untrusted':'Untrusted recovery configuration file', 'invalid':'format_version'}[args.case]
                    assert expected in reason, reason
                    assert not window.buttons[3][0].get_sensitive()
                    assert window.buttons[4][0].get_sensitive()
                    assert window.status['destinations'] == []
                    result.append(dict(case=args.case, diagnostic_only=True, displayed_reason=reason))
                    Gtk.main_quit()
                    return False
            return True
        GLib.timeout_add(25, inspect)
        # Execute the installed main's actual no-argument branch, not --fixture.
        sys.argv = [str(args.runtime / 'sv08_recovery_ui.py')]
        installed_main()
        assert len(result) == 1
        print(json.dumps(result[0]))
        return
    mounted = []
    try:
        for target in ('/etc', '/run'):
            subprocess.run(['mount', '-t', 'tmpfs', '-o', 'mode=0755,nosuid,nodev', 'tmpfs', target], check=True)
            mounted.append(target)
        Path('/etc/sv08').mkdir()
        Path('/run/sv08-recovery').mkdir(mode=0o700)
        Path('/run/sv08-recovery/media-context.json').write_text('{}')
        policy = Path('/etc/sv08/recovery-media-policy.json')
        for case in ('absent', 'malformed', 'untrusted', 'invalid'):
            if case != 'absent':
                policy.write_text('{broken' if case == 'malformed' else '{}')
                policy.chmod(0o666 if case == 'untrusted' else 0o644)
            subprocess.run(['xvfb-run', '-a', '/usr/bin/python3', str(Path(__file__).resolve()),
                            '--runtime', str(args.runtime.resolve()), '--case', case],
                           check=True, timeout=30, env={**os.environ, 'NO_AT_BRIDGE':'1', 'GSETTINGS_BACKEND':'memory'})
    finally:
        for target in reversed(mounted):
            subprocess.run(['umount', target], check=True)


if __name__ == '__main__': main()
