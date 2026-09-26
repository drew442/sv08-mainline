#!/usr/bin/python3
"""Exercise the signed feed through the real RAUC transaction on QEMU media."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit


def require(value, message):
    if not value:
        raise AssertionError(message)


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def environment():
    values = {}
    for line in command('/usr/bin/fw_printenv', '-c', '/etc/fw_env.config').splitlines():
        if '=' in line:
            name, value = line.split('=', 1)
            values[name] = value
    return values


def environment_copies():
    result = []
    target = Path(Path('/etc/fw_env.config').read_text().split()[0])
    fd = target.open('rb', buffering=0)
    try:
        for offset in (0x400000, 0x800000):
            result.append(hashlib.sha256(__import__('os').pread(fd.fileno(), 0x10000, offset)).hexdigest())
    finally:
        fd.close()
    return result


def main():
    require(command('/usr/bin/systemd-detect-virt', '--vm') == 'qemu', 'not QEMU')
    env_entries = [line.split() for line in Path('/etc/fw_env.config').read_text().splitlines() if line.strip()]
    require(len(env_entries) == 2 and env_entries[0][0] == env_entries[1][0] and
            [entry[1:] for entry in env_entries] == [['0x400000', '0x10000'], ['0x800000', '0x10000']],
            'unexpected fixture environment map')
    target_name = Path(env_entries[0][0]).name
    require(Path('/sys/block', target_name, 'serial').read_text().strip() == 'SV08-QEMU-TARGET',
            'environment does not address the identified target disk')
    require(Path('/run/sv08/fixture-feed/sv08/feed-1').is_dir(),
            'read-only signed feed fixture was not mounted')
    require('sv08.test=rauc-backend' in Path('/proc/cmdline').read_text().split(), 'missing fixture guard')
    ready = Path('/run/sv08/os-health-ready')
    require(ready.is_file(), 'production boot-health gate did not pass')
    runtime = Path('/usr/lib/sv08')
    manifest = json.loads((runtime / 'release.json').read_text())
    policy = json.loads((runtime / 'update-policy.json').read_text())
    layout = json.loads((runtime / 'layout.json').read_text())
    env_layout = json.loads((runtime / 'environment.json').read_text())
    require(manifest['deployable'] is False, 'fixture became deployable')
    sys.path.insert(0, str(runtime))
    from sv08_admission import Admission
    from sv08_bundle import inspect as inspect_bundle
    from sv08_feed import Feed
    from sv08_rauc import Backend
    from sv08_staging import Staging
    from sv08_state import Store, atomic_json
    from sv08_transaction import Transaction

    phase_path = Path('/data/sv08/qemu-update-phase.json')
    phase = json.loads(phase_path.read_text())
    step = phase['step']
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    store = Store('/data/sv08')
    state = store.load()
    backend = Backend(manifest, policy, layout, env_layout, fixture=True)
    tx = Transaction(store, backend, Admission())
    fixture = Path('/run/sv08/fixture-feed')
    subprocess.run(['/usr/bin/systemctl', 'start', 'rauc.service'], check=True)

    if step in (0, 1):
        source = ('A', 'B')[step]
        target = ('B', 'A')[step]
        # The B-to-A fixture starts after this boot's trial has been confirmed.
        # /run/sv08/boot.json remains an immutable record of how B was entered,
        # so its trial bit correctly stays true for the duration of that boot.
        require(boot['slot'] == source and boot['trial'] is (step == 1),
                'unexpected healthy source slot/trial identity')
        require(ready.is_file(), 'healthy source marker missing')
        require(state['auto_update'] is True, 'automatic policy did not default on')
        current = tx.load()
        if step == 0:
            require(current is None and backend.primary() == 'A', 'first source is not clean A')
        else:
            require(current and current['phase'] == 'complete' and backend.primary() == 'B',
                    'first B trial was not health-confirmed')
        feed_dir = fixture / 'sv08' / ('feed-' + str(step + 1))
        before_env, before_copies = environment(), environment_copies()
        disarm_observation = {}
        original_disarm = backend.disarm_target

        def capture_disarm(slot, running):
            require(environment() == before_env, 'boot policy changed before journaled pre-disarm')
            original_disarm(slot, running)
            after = environment()
            changed = sorted(key for key in set(before_env) | set(after) if before_env.get(key) != after.get(key))
            allowed = {'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT'}
            require(set(changed) <= allowed, 'pre-disarm changed unexpected environment fields: ' + repr(changed))
            require(after['BOOT_ORDER'].split()[0] == running, 'pre-disarm changed the selected source')
            require(after['BOOT_'+slot+'_LEFT'] == '0' and slot not in after['BOOT_ORDER'].split(),
                    'pre-disarm did not exclude target')
            require(after['BOOT_'+running+'_LEFT'] == before_env['BOOT_'+running+'_LEFT'],
                    'pre-disarm changed source attempts')
            disarm_observation.update(environment=after, copies=environment_copies(), changed=changed)

        backend.disarm_target = capture_disarm
        original = backend.mark_active
        arm_observation = {}

        def capture_arm(slot):
            baseline_env = disarm_observation.get('environment', before_env)
            baseline_copies = disarm_observation.get('copies', before_copies)
            require(environment() == baseline_env, 'RAUC staging changed boot policy after pre-disarm')
            require(environment_copies() == baseline_copies, 'RAUC staging changed raw environment copies after pre-disarm')
            arm_observation['stage_env_unchanged'] = True
            original(slot)
            after = environment()
            changed = sorted(key for key in set(before_env) | set(after) if before_env.get(key) != after.get(key))
            allowed = {'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT'}
            require(set(changed) <= allowed and 'BOOT_ORDER' in changed, 'unexpected environment delta: ' + repr(changed))
            require(after['BOOT_ORDER'].split()[0] == target, 'arm did not select inactive target')
            require(int(after['BOOT_' + target + '_LEFT']) > 0, 'arm left the target unbootable')
            arm_observation.update(armed_environment=after, changed_environment=changed,
                                   stage_environment_before=baseline_env,
                                   stage_environment_copies=baseline_copies)

        backend.mark_active = capture_arm
        config = dict(format_version=1, url='https://fixture.invalid/sv08/stable/', channel='stable',
                      ca_file='/usr/lib/sv08/fixture-signers.pem',
                      signer_ca_file='/usr/lib/sv08/fixture-signers.pem')

        def fetch(url, limit, deadline):
            name = urlsplit(url).path.rsplit('/', 1)[-1]
            candidate = feed_dir / name
            require(candidate.is_file() and candidate.stat().st_size <= limit, 'missing/oversized signed feed object')
            return candidate.open('rb')

        now = int(phase['trusted_now'])
        verify = lambda bundle: inspect_bundle(bundle, policy, backend.keyring)
        feed = Feed(store, Staging('/data/sv08/feed-bundles', max_bytes=policy['max_bundle_bytes']),
                    tx, boot, verify, config, now=lambda: now, fetch=fetch)
        result = feed.run()
        require(result == 'armed-next-boot' and arm_observation.get('stage_env_unchanged'), 'feed did not stage then arm')
        transaction = tx.load()
        require(transaction['phase'] == 'armed' and transaction['slot'] == target and
                transaction['previous_slot'] == source, 'journal differs from feed target')
        require(store.load()['pending']['slot'] == target, 'persistent trial was not armed')
        phase.update(step=step + 1)
        atomic_json(phase_path, phase)
        print('SV08_QEMU_SIGNED_FEED_ARM ' + json.dumps(dict(step=step, source=source, target=target,
              release=transaction['release'], stage_environment_unchanged=True,
              pre_disarm_environment_delta=disarm_observation.get('changed', []),
              pre_disarm_environment_copies=disarm_observation.get('copies', before_copies),
              changed_environment=arm_observation['changed_environment']), sort_keys=True), flush=True)
    else:
        require(step == 2 and boot['slot'] == 'B' and not boot['trial'], 'unexpected final fallback boot')
        transaction = tx.load()
        state = store.load()
        require(transaction and transaction['phase'] == 'failed', 'failed A trial was not cancelled after fallback')
        require(state['pending'] is None and state.get('last_failed_trial', {}).get('slot') == 'A',
                'failed A trial was not retained')
        require(backend.primary() == 'B' and backend.good('B'), 'preserved B fallback is not selected and good')
        require((Path('/data/fixture/user-data-sentinel')).read_text() == 'preserved fixture data\n',
                'persistent user artifact changed')
        print('SV08_QEMU_SIGNED_FEED_COMPLETE ' + json.dumps(dict(passed=True, source_a_to_b=True,
              source_b_to_a_trial=True, a_trial_rejected=True, b_fallback_confirmed=True,
              automatic_policy=True, physical_hardware=False, shared_user_data_preserved=True), sort_keys=True),
              flush=True)
        phase.update(step=3)
        atomic_json(phase_path, phase)
    subprocess.run(['/usr/bin/systemctl', 'poweroff'], check=False, timeout=20)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print('SV08_QEMU_SIGNED_FEED_FAILURE ' + repr(error), flush=True)
        raise
    finally:
        subprocess.run(['/usr/bin/systemctl', 'poweroff'], check=False, timeout=20)
