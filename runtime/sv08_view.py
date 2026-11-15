#!/usr/bin/env python3
"""Finite root read entry. Install root-owned; invoke only with isolated Python.

The caller supplies an area and a read method, never a path or child request.
Existing write helpers remain root-only. This entry does not grant a bridge.
"""
import json
import os
import re
import subprocess
import sys

LIMIT = 16384
OUTPUT_LIMIT = 8 * 1024 * 1024
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/root'}
SCRIPTS = {name: '/usr/lib/sv08/sv08_' + script + '.py' for name, script in
           [('host', 'admin'), ('printer', 'printer_helper'), ('network', 'network'),
            ('software', 'software'), ('identity', 'identity'), ('mainsail-access', 'mainsail_access'),
            ('provenance', 'provenance')]}
FIELDS = {
    'host': 'context revision boot requested_mode auto_update update_policy slots pending transaction free_bytes capabilities catalog destinations images hostname feed_status'.split(),
    'printer': 'state catalog available_components native_calibration_status context catalog_revision catalog_supported loaded_identity definitions sources migration_available'.split(),
    'network': 'devices connections hostname fqdn pending'.split(),
    'software': 'boot requested_mode customized catalog capabilities storage jobs reconciliation'.split(),
    'identity': 'revision ca_fingerprint ssh_fingerprint authorized_keys service_names healthy'.split(),
    'mainsail-access': 'authority_valid warning mode username managed ca_fingerprint certificates'.split(),
}
SECRET_FIELDS = {'password', 'password_hash', 'hash', 'private_key', 'ca_key', 'pkcs12_base64', 'bundle', 'content', 'data', 'secret'}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate field')
        result[key] = value
    return result


def validate(request):
    if not isinstance(request, dict): raise ValueError('Expected view object')
    expected = {'area','method','id'} if request.get('area') == 'software' and request.get('method') == 'inspect' else {'area','method'}
    if set(request) != expected: raise ValueError('Unexpected view fields')
    area, method = request['area'], request['method']
    if not isinstance(area, str) or area not in SCRIPTS or not isinstance(method, str):
        raise ValueError('Unknown view')
    if area == 'software' and method == 'inspect':
        if not isinstance(request['id'],str) or not re.fullmatch('[0-9a-f]{32}',request['id']): raise ValueError('Invalid receipt')
    elif method != 'status' and not (area == 'host' and method in ('jobs', 'upload.list')) and not (area == 'identity' and method == 'ca.download'):
        raise ValueError('Unknown read operation')
    return area, method


def public(area, method, result):
    if not isinstance(result, dict): raise ValueError('Invalid read response')
    if area == 'provenance':
        fields = {'state', 'build_id', 'scope', 'reason'}
        result = {key: result[key] for key in fields if key in result}
        reasons = {'intact': {'record-matches'}, 'tainted': {'record-mismatch'},
                   'unavailable': {'baseline-missing', 'read-failed'}}
        if (set(result) != fields or result['scope'] != 'local-project-record' or
                not isinstance(result['state'], str) or result['state'] not in reasons or
                not isinstance(result['reason'], str) or result['reason'] not in reasons[result['state']] or
                (result['state'] == 'intact' and (not isinstance(result['build_id'], str) or
                    not re.fullmatch('[a-f0-9]{64}', result['build_id']))) or
                (result['state'] != 'intact' and result['build_id'] is not None)):
            raise ValueError('Invalid provenance response')
        return result
    if area == 'identity' and method == 'ca.download':
        if set(result) != {'filename','content'} or result['filename'] != 'sv08-printer-ca.crt' or not isinstance(result['content'],str) or len(result['content'])>65536 or not re.fullmatch(r'-----BEGIN CERTIFICATE-----\n[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----\n?', result['content']):
            raise ValueError('Invalid public certificate')
        return result
    if area == 'software' and method == 'inspect':
        fields = ['job','evidence','dpkg_audit','policy_recovery_required','policy_recoverable','warning']
    else: fields = FIELDS[area] if method == 'status' else (
        'history_revision active archives total total_capacity total_remaining maintenance_available maintenance_reason format jobs capacity remaining blocked'.split()
        if method == 'jobs' else ['objects', 'busy', 'message'])
    # Future helper fields are never exposed implicitly.
    result = {key: result[key] for key in fields if key in result}
    def inspect(value):
        if isinstance(value, dict):
            if SECRET_FIELDS.intersection(value): raise ValueError('Private response refused')
            for child in value.values(): inspect(child)
        elif isinstance(value, list):
            for child in value: inspect(child)
    inspect(result)
    return result


def child_code(area):
    prefix = "import sys,runpy;sys.path.insert(0,'/usr/lib/sv08');"
    if area == 'mainsail-access':
        # request(status) recovers a journal. Viewing must never recover/reload.
        return prefix + ("import json;from sv08_mainsail_access import MainsailAccess;"
                         "b=MainsailAccess();\nwith b.budget.locked():\n"
                         " p=b.load();r=b.status(p if p is not None else b.initial(),p is not None)\n"
                         "print(json.dumps({'ok':True,'result':r}))")
    return prefix + 'runpy.run_path(' + repr(SCRIPTS[area]) + ",run_name='__main__')"


def read(request):
    area, method = validate(request)
    child = {'action': 'status'} if area == 'printer' else {'method': method}
    if area == 'software' and method == 'inspect': child['id'] = request['id']
    command = ['/usr/bin/python3', '-I'] + (['-B'] if area == 'provenance' else [])
    result = subprocess.run([*command, '-c', child_code(area)],
                            input=json.dumps(child), text=True, capture_output=True,
                            cwd='/', env=ENV, timeout=30)
    if result.returncode or len(result.stdout.encode()) > OUTPUT_LIMIT:
        raise ValueError('Read unavailable')
    reply = json.loads(result.stdout, object_pairs_hook=unique)
    if not isinstance(reply, dict) or reply.get('ok') is not True:
        raise ValueError('Read unavailable')
    return public(area, method, reply['result'])


def main():
    try:
        if sys.argv[1:] or os.geteuid() != 0: raise ValueError('Invalid entry')
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT: raise ValueError('Oversized request')
        result = read(json.loads(raw, object_pairs_hook=unique))
        print(json.dumps({'ok': True, 'result': result}, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError, RecursionError, subprocess.SubprocessError):
        # No child stderr, parser text, credential values or private paths.
        print(json.dumps({'ok': False, 'error': 'Configuration view unavailable. Refresh or ask an administrator to inspect the host.'}))
    return 0


if __name__ == '__main__': sys.exit(main())
