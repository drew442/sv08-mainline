#!/usr/bin/env python3
"""Export upstream uv runtime lock for CPython 3.13 Linux ARM64, without resolving.

Gap: image packaging needs a target-specific input lock independent of workstation markers.
Use upstream uv.lock as provenance. Retire when the common builder uses uv's
frozen target export directly. No downloads or hardware operations here.
"""
import argparse
import json
from pathlib import Path
import tomllib
from packaging.markers import Marker, default_environment
from packaging.tags import cpython_tags, compatible_tags
from packaging.utils import parse_wheel_filename


def select(lock):
    env = default_environment()
    env.update(python_version='3.13', python_full_version='3.13.5',
               implementation_name='cpython', implementation_version='3.13.5',
               platform_python_implementation='CPython', platform_machine='aarch64',
               sys_platform='linux', os_name='posix', platform_system='Linux', extra='')
    platforms = [f'manylinux_2_{n}_aarch64' for n in range(41, 16, -1)]
    platforms += ['manylinux2014_aarch64', 'linux_aarch64']
    tags = list(cpython_tags((3, 13), platforms=platforms))
    tags += list(compatible_tags((3, 13), interpreter='cp313', platforms=platforms))
    rank = {t: i for i, t in enumerate(tags)}
    selected = {}
    pending = [{'name': 'moonraker'}]
    while pending:
        dep = pending.pop()
        if dep.get('marker') and not Marker(dep['marker']).evaluate(env):
            continue
        name = dep['name']
        if name in selected:
            if dep.get('version') and selected[name].get('version') != dep['version']:
                raise ValueError('Conflicting locked versions: ' + name)
            continue
        candidates = [p for p in lock['package'] if p['name'] == name
                      and (not dep.get('version') or p.get('version') == dep['version'])
                      and (not p.get('resolution-markers') or
                           any(Marker(m).evaluate(env) for m in p['resolution-markers']))]
        if len(candidates) != 1:
            raise ValueError('Ambiguous/missing locked package: ' + name)
        pkg = candidates[0]
        selected[name] = pkg
        pending.extend(pkg.get('dependencies', []))
    result = []
    for name, pkg in sorted(selected.items()):
        if name == 'moonraker':
            continue
        candidates = []
        for wheel in pkg.get('wheels', []):
            filename = wheel['url'].rsplit('/', 1)[1]
            matches = parse_wheel_filename(filename)[3] & rank.keys()
            if matches:
                candidates.append((min(rank[t] for t in matches), filename, wheel))
        if not candidates:
            wheel = pkg['sdist']
            filename = wheel['url'].rsplit('/', 1)[1]
        else:
            _, filename, wheel = min(candidates)
        result.append(dict(name=name, version=pkg['version'], filename=filename,
                           requires_build=not bool(candidates),
                           url=wheel['url'], sha256=wheel['hash'].removeprefix('sha256:')))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('upstream/moonraker/uv.lock'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    entries = select(tomllib.loads(a.source.read_text()))
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'wheels.json').write_text(json.dumps(entries, indent=2) + '\n')
    (a.output / 'requirements.lock').write_text(''.join(
        f"{x['name']}=={x['version']} --hash=sha256:{x['sha256']}\n" for x in entries))


if __name__ == '__main__':
    main()
