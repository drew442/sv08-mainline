#!/usr/bin/env python3
"""Read compiled SV08 U-Boot inputs and test its default guard in sandbox."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.check_output([str(a) for a in args], text=True, timeout=45)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--sandbox', type=Path, required=True)
    a = p.parse_args()
    uboot = a.build / 'u-boot-source'
    profile = json.loads((REPO / 'configs/host-os/sv08-boot-compile-candidate.json').read_text())
    config = (uboot / '.config').read_text()
    for key, value in profile['integration']['expected_config'].items():
        line = '# ' + key + ' is not set' if value == 'n' else key + '=' + value
        assert line in config.splitlines(), line
    dtb = uboot / 'u-boot.dtb'
    def get(node, prop, kind='s'):
        return run('fdtget', '-t', kind, dtb, node, prop).strip()
    assert get('/', 'model') == 'Sovol SV08 test-sv08-01 U-Boot diagnostic'
    assert 'leds' not in run('fdtget', '-l', dtb, '/').splitlines()
    assert get('/aliases', 'mmc0') == '/soc/mmc@4020000'
    assert get('/aliases', 'mmc1') == '/soc/mmc@4022000'
    assert get('/soc/mmc@4021000', 'status') == 'disabled'
    assert get('/bootstd', 'bootdev-order') == 'mmc1'
    assert get('/bootstd/rauc', 'compatible') == 'u-boot,distro-rauc'
    assert 'gpio' not in run('fdtget', '-p', dtb, '/regulator-usb1-vbus').splitlines()
    # Read the actual linked ELF symbol, not only its generated source header.
    elf = uboot / 'u-boot'
    symbols = run('aarch64-linux-gnu-nm', '-S', elf)
    match = re.search(r'^([0-9a-f]+) ([0-9a-f]+) R default_environment$', symbols, re.M)
    address, size = (int(v, 16) for v in match.groups())
    sections = run('aarch64-linux-gnu-readelf', '-SW', elf)
    section = re.search(r'\.rodata\s+PROGBITS\s+([0-9a-f]+)\s+([0-9a-f]+)', sections)
    base, offset = (int(v, 16) for v in section.groups())
    data = elf.read_bytes()[offset + address - base:offset + address - base + size]
    entries = [s.decode().split('=', 1) for s in data.split(b'\0') if s]
    env = dict(entries)
    assert len(entries) == len(env)
    intended = dict(line.split('=', 1) for line in
                    (REPO / 'configs/host-os/sv08-default.env').read_text().splitlines())
    assert env == intended
    assert not {'sv08_env_layout', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT'} & env.keys()
    assert env['bootcmd'] == 'run sv08_dispatch'
    lines = []
    for line in (REPO / 'configs/host-os/boot-dispatch.cmd').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        lines.append(line if line.endswith(('then', 'else', ';')) else line + ';')
    assert env['sv08_dispatch'] == ' '.join(lines)
    cases = [dict(), dict(sv08_env_layout='wrong'),
             dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B', BOOT_A_LEFT='0', BOOT_B_LEFT='0'),
             dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A', BOOT_A_LEFT='0', BOOT_B_LEFT='3'),
             dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B', BOOT_A_LEFT='bad', BOOT_B_LEFT='3')]
    for values in cases:
        trial = env | values
        # Only sandbox load address/device discovery differ from board inputs.
        trial['scriptaddr'] = '0x100000'
        command = 'env default -a; setenv BOOT_ORDER; setenv BOOT_A_LEFT; setenv BOOT_B_LEFT; '
        for key, value in trial.items():
            assert "'" not in value
            command += f"setenv {key} '{value}'; "
        output = run(a.sandbox.resolve(), '-c', command + 'run bootcmd')
        assert 'SV08: recovery unavailable; restore using the USB eMMC reader' in output, output
        assert 'syntax error' not in output and 'Scanning' not in output, output
    # Verify that the selected DT is actually carried in the final FIT.
    with tempfile.TemporaryDirectory(prefix='sv08-fit-check-') as td:
        target = Path(td) / 'selected.dtb'
        run(uboot / 'tools/dumpimage', '-T', 'flat_dt', '-p', '2', '-o', target,
            uboot / 'u-boot-sunxi-with-spl.fit.fit')
        assert target.read_bytes() == dtb.read_bytes()
    print(json.dumps(dict(passed=True, compiled_environment_sha256=hashlib.sha256(data).hexdigest(),
                         invalid_state_cases=len(cases), selected_fit_dtb_matches=True,
                         physical_boot_validated=False)))


if __name__ == '__main__':
    main()
