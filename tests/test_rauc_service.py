import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'runtime'))
from sv08_rauc_service import Service

REAL_FSTAT = os.fstat


class Result:
    def __init__(self, data=None, code=0, error=''):
        self.returncode, self.stdout, self.stderr = code, json.dumps({'data': data}), error


class ServiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.policy = self.root / 'policy.json'
        self.policy.write_text((REPO / 'configs/host-os/rauc-service-policy.json').read_text())
        self.lock = self.root / 'writer.lock'

    def root_lock_stat(self, fd):
        value = REAL_FSTAT(fd)
        return SimpleNamespace(st_mode=value.st_mode, st_uid=0, st_nlink=value.st_nlink)

    def test_policy_is_pinned_to_built_arm64_executable(self):
        value = Service(self.policy, self.lock).policy()
        self.assertEqual(value['version'], '1.15.2-0sv08.1')
        self.assertEqual(value['executable_sha256'], '51d7c057c7fb00917287b5324303c747e71c5406f4c1363a678578ac7a3b12e3')
        value['version'] = 'unreviewed'; self.policy.write_text(json.dumps(value))
        # Version changes are schema-valid policy input, but an identity probe
        # must compare it with dpkg before any writer action.
        self.assertEqual(Service(self.policy, self.lock).policy()['version'], 'unreviewed')

    def test_call_refuses_busy_and_malformed_service_answers(self):
        busy = Service(self.policy, self.lock, lambda *args, **kwargs: Result(code=1, error='already processing a different method'))
        with self.assertRaisesRegex(ValueError, 'internally busy'):
            busy.call(':1.4', 'de.pengutronix.rauc.Installer', 'GetSlotStatus')
        malformed = Service(self.policy, self.lock, lambda *args, **kwargs: type('R', (), {'returncode': 0, 'stdout': '{}', 'stderr': ''})())
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            malformed.call(':1.4', 'de.pengutronix.rauc.Installer', 'GetSlotStatus')

    def test_identity_refuses_package_or_systemd_execution_failure(self):
        service = Service(self.policy, self.lock)
        service.call = lambda *_: [os.getpid()]
        policy = service.policy()
        failures = {
            'package': [subprocess.TimeoutExpired('dpkg-query', 10)],
            'systemd': [policy['version'], subprocess.TimeoutExpired('systemctl', 10)],
        }
        for name, side_effect in failures.items():
            with self.subTest(name=name), \
                 patch('sv08_rauc_service.Path.resolve', return_value=Path('/usr/bin/rauc')), \
                 patch.object(Service, 'digest', return_value=policy['executable_sha256']), \
                 patch('sv08_rauc_service.subprocess.check_output', side_effect=side_effect):
                with self.assertRaisesRegex(ValueError, 'process identity is unavailable'):
                    service.identity(':1.41', policy)

    def test_observation_requires_writer_and_uses_internal_busy_guard(self):
        calls = []
        answers = iter([
            ['bus-id'], [':1.4'], [0], [{'data': 'idle'}], [[['rootfs.0', {}]]], ['bus-id'], [':1.4'],
        ])
        service = Service(self.policy, self.lock)
        service.call = lambda destination, interface, method, *args: calls.append((destination, interface, method)) or next(answers)
        service.identity = lambda owner, policy: {'pid': 42, 'package': policy['version']}
        with self.assertRaisesRegex(ValueError, 'requires writer'):
            service.observe()
        with patch('sv08_rauc_service.os.geteuid', return_value=0), patch('sv08_rauc_service.os.fstat', self.root_lock_stat):
            with service.writer():
                observed = service.observe()
        self.assertEqual(observed['busy_guard'], 'GetSlotStatus')
        self.assertIn((':1.4', 'de.pengutronix.rauc.Installer', 'GetSlotStatus'), calls)

    def test_writer_exclusion_is_nonblocking_and_reentrant(self):
        first, second = Service(self.policy, self.lock), Service(self.policy, self.lock)
        with patch('sv08_rauc_service.os.geteuid', return_value=0), patch('sv08_rauc_service.os.fstat', self.root_lock_stat):
            with first.writer():
                with first.writer():
                    self.assertEqual(first.depth, 2)
                with self.assertRaisesRegex(ValueError, 'writer is active'):
                    with second.writer():
                        pass
            with second.writer():
                self.assertEqual(second.depth, 1)
