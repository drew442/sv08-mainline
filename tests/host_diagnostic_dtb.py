#!/usr/bin/env python3
"""Check effective diagnostic DTB properties, including inherited board nodes.

Run against the compiled diagnostic artifact, not its DTS text. This does not
verify physical wiring or replace dt-schema/hardware testing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def verify(path):
    def get(node, prop, kind='s'):
        return subprocess.check_output(
            ['fdtget', '-t', kind, str(path), node, prop], text=True
        ).strip()

    def symbol(name):
        return get('/__symbols__', name)

    checks = {}
    for name, low, high in (
        ('reg_dcdc1', 810000, 990000),
        ('reg_dcdc2', 810000, 1100000),
        ('reg_dcdc3', 1350000, 1500000),
    ):
        node = symbol(name)
        limits = [int(get(node, p, 'u')) for p in
                  ('regulator-min-microvolt', 'regulator-max-microvolt')]
        assert limits == [low, high], (name, limits)
        checks[name] = limits
    assert get(symbol('gpu'), 'status') == 'disabled'
    checks['gpu_disabled'] = True
    assert get(symbol('cpu_critical'), 'temperature', 'u') == '105000'
    assert get(symbol('cpu_critical'), 'hysteresis', 'u') == '2000'
    checks['cpu_critical_millicelsius'] = 105000
    for name in ('cpu0', 'cpu1', 'cpu2', 'cpu3'):
        props = subprocess.check_output(
            ['fdtget', '-p', str(path), symbol(name)], text=True
        ).splitlines()
        assert 'operating-points-v2' not in props, name
    checks['cpu_opp_references_absent'] = True
    for name in ('de', 'hdmi', 'mmc2', 'emac1', 'uart0'):
        assert get(symbol(name), 'status') == 'okay', name
        checks[name] = 'okay'
    assert get(symbol('mmc2'), 'bus-width', 'u') == '8'
    assert get(symbol('mmc2'), 'max-frequency', 'u') == '45000000'
    props = subprocess.check_output(
        ['fdtget', '-p', str(path), symbol('mmc2')], text=True
    ).splitlines()
    assert 'no-1-8-v' in props
    assert get('/chosen', 'stdout-path') == 'serial0:115200n8'
    for name in ('ws2812', 'i2c_gpio', 'can', 'tft_35'):
        assert get(symbol(name), 'status') == 'disabled', name
    return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                checks=checks, hardware_validated=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dtb', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.dtb), indent=2))
