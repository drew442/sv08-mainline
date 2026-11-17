"""Release-bound MCU recommendations and read-only Klipper observations.

Recommendations are software revisions, never flashing instructions or evidence
of board identity, clocks, offsets, protocol compatibility or commissioning.
"""
import json
from pathlib import Path
import re
import socket
import stat
import time

from sv08_printer_catalog import digest, strict_json

EXTENSION = 'sv08.mcu_firmware'
LIMIT = 65536
SOCKET = '/run/sv08/printer_data/comms/klippy.sock'
COMMIT = re.compile(r'[0-9a-f]{40}\Z')
ROLE = re.compile(r'[a-z][a-z0-9_]{0,39}\Z')


def recommendation(value):
    if (not isinstance(value, dict) or set(value) != {'format_version', 'klipper_commit'}
            or type(value['format_version']) is not int or value['format_version'] != 1
            or not isinstance(value['klipper_commit'], str) or not COMMIT.fullmatch(value['klipper_commit'])):
        raise ValueError('MCU firmware recommendation requires an exact Klipper commit')
    return value


def release_assignment(release, host_commit, definitions):
    """Snapshot complete board definitions, rather than re-resolving latest IDs."""
    rows = []
    for definition in definitions:
        value = definition.get('extensions', {}).get(EXTENSION)
        if value is None: continue
        recommendation(value)
        if definition.get('kind') != 'board' or value['klipper_commit'] != host_commit:
            raise ValueError('MCU recommendation must match the pinned release host')
        rows.append(dict(reference=dict(source='builtin', id=definition['id'], version=definition['version'],
                                        sha256=digest(definition)), definition=definition))
    value = dict(format_version=1, release=release, host_klipper_commit=host_commit, definitions=rows)
    validate_assignment(value, release)
    if len(json.dumps(value).encode()) > LIMIT: raise ValueError('MCU assignment exceeds bound')
    return value


def validate_assignment(value, release):
    if (not isinstance(value, dict) or set(value) != {'format_version', 'release', 'host_klipper_commit', 'definitions'}
            or type(value['format_version']) is not int or value['format_version'] != 1 or value['release'] != release
            or not isinstance(value['host_klipper_commit'], str) or not COMMIT.fullmatch(value['host_klipper_commit'])
            or not isinstance(value['definitions'], list) or len(value['definitions']) > 16):
        raise ValueError('Invalid release MCU assignment')
    seen = set()
    for row in value['definitions']:
        if not isinstance(row, dict) or set(row) != {'reference', 'definition'}: raise ValueError('Invalid MCU definition snapshot')
        definition, ref = row['definition'], row['reference']
        if (not isinstance(definition, dict) or definition.get('kind') != 'board'
                or ref != dict(source='builtin', id=definition.get('id'), version=definition.get('version'), sha256=digest(definition))):
            raise ValueError('MCU definition snapshot digest differs')
        rec = recommendation(definition.get('extensions', {}).get(EXTENSION))
        mapping = definition.get('mapping', {})
        if not isinstance(mapping,dict):raise ValueError('Invalid MCU definition mapping')
        if rec['klipper_commit'] != value['host_klipper_commit'] or not isinstance(mapping.get('id'), str):
            raise ValueError('MCU definition differs from release host')
        if mapping['id'] in seen: raise ValueError('Duplicate MCU board recommendation')
        seen.add(mapping['id'])
    return value


def read_regular(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)): raise ValueError('Unexpected MCU assignment link')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > LIMIT:
        raise ValueError('Invalid MCU assignment file')
    return strict_json(path.read_bytes(), LIMIT)


def installed_assignment(release, schema, path=Path('/usr/lib/sv08/release.json')):
    path = Path(path)
    if not path.exists(): return None
    manifest = read_regular(path)
    if manifest.get('release') != release or manifest.get('state_schema') != schema: return None
    value = manifest.get('mcu_firmware')
    return validate_assignment(value, release) if value is not None else None


def applied_boards(draft, catalog):
    """Non-private mapping captured in the same reviewed publication as config."""
    from sv08_printer_fields import compact_mapping
    return {role: dict(id=board['id'], mapping_sha256=digest(compact_mapping(catalog.boards[board['id']])))
            for role, board in draft['boards'].items()}


def observe():
    """Only fixed read operations over the fixed local UDS; bounded total time."""
    deadline = time.monotonic() + 2
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(2)
        client.connect(SOCKET)
        buffer = b''
        def call(ident, method, params):
            nonlocal buffer
            client.sendall(json.dumps(dict(id=ident, method=method, params=params)).encode()+b'\x03')
            while True:
                client.settimeout(max(.001, deadline-time.monotonic()))
                if time.monotonic() >= deadline: raise TimeoutError('MCU observation timed out')
                if b'\x03' not in buffer:
                    chunk = client.recv(16384)
                    if not chunk: raise ValueError('Klipper unavailable')
                    buffer += chunk
                    if len(buffer) > LIMIT: raise ValueError('MCU observation exceeds bound')
                    continue
                raw, buffer = buffer.split(b'\x03', 1)
                reply = strict_json(raw, LIMIT)
                if not isinstance(reply,dict):raise ValueError('Invalid MCU observation response')
                if reply.get('id') != ident: continue
                if 'error' in reply: raise ValueError('MCU observation unavailable')
                if not isinstance(reply.get('result'),dict):raise ValueError('Invalid MCU observation result')
                return reply['result']
        objects = call(1, 'objects/list', {})['objects']
        if not isinstance(objects,list):raise ValueError('Invalid MCU object list')
        names = [n for n in objects if isinstance(n, str) and (n == 'mcu' or n.startswith('mcu ') and ROLE.fullmatch(n[4:]))]
        if len(names) > 16: raise ValueError('Too many MCU objects')
        return call(2, 'objects/query', {'objects': {n: ['mcu_version'] for n in names}})['status']


def revision(version):
    if not isinstance(version, str) or len(version) > 160: return None
    match = re.fullmatch(r'[^\s]*-g([0-9a-f]{7,40})', version)
    return match[1] if match else None


def status(generation, release, publisher, context, observer=None):
    """Advisory only. Unknown observations never imply compatible or matching."""
    result = dict(release=release, state='unknown', message='MCU firmware recommendation or applied board mapping is unavailable.', boards=[])
    try:
        assignment = validate_assignment(read_regular(Path(generation)/'mcu-firmware.json'), release)
    except (OSError, ValueError, KeyError, TypeError):
        assignment = None
    try:
        receipt, _, _, _ = publisher.active_calibration(context)
        boards = receipt['native']['binding']['firmware_boards']
        if (not isinstance(boards, dict) or len(boards) > 16
                or any(not isinstance(k,str) or not ROLE.fullmatch(k) or not isinstance(v,dict)
                       for k,v in boards.items())): raise ValueError('Invalid applied board mapping')
    except (OSError, ValueError, KeyError, TypeError):
        boards = {}
    try:
        observed = (observer or observe)()
        if not isinstance(observed, dict): observed = {}
    except (OSError, ValueError, KeyError, TypeError, TimeoutError):
        observed = {}
    definitions = (assignment or {}).get('definitions', [])
    roles = set(boards) | {('main' if name == 'mcu' else name[4:]) for name in observed
                           if name == 'mcu' or isinstance(name, str) and name.startswith('mcu ') and ROLE.fullmatch(name[4:])}
    for role in sorted(roles):
        if not isinstance(role, str) or not ROLE.fullmatch(role): continue
        board = boards.get(role, {})
        expected = next((r for r in definitions if r['definition']['mapping']['id'] == board.get('id')
                         and digest(r['definition']['mapping']) == board.get('mapping_sha256')), None)
        commit = expected['definition']['extensions'][EXTENSION]['klipper_commit'] if expected else None
        observation = observed.get('mcu' if role == 'main' else 'mcu '+role, {})
        raw = observation.get('mcu_version') if isinstance(observation,dict) else None
        raw = raw if isinstance(raw, str) and len(raw) <= 160 and all(ord(c) >= 32 for c in raw) else None
        actual = revision(raw)
        state = ('match' if commit.startswith(actual) else 'mismatch') if commit and actual else 'unknown'
        result['boards'].append(dict(role=role, expected_commit=commit, observed_version=raw, state=state,
                                     definition=expected['reference'] if expected else None))
    states = [b['state'] for b in result['boards']]
    result['state'] = 'mismatch' if 'mismatch' in states else 'match' if states and all(s == 'match' for s in states) else 'unknown'
    result['message'] = {'match': 'Reported MCU firmware matches this system release’s recommendation. This does not establish hardware compatibility or commissioning.',
                         'mismatch': 'Reported MCU firmware differs from this system release’s recommendation. Check compatibility before printing. System updates and rollback do not flash MCU firmware.',
                         'unknown': 'MCU firmware could not be compared with this system release’s recommendation. Check the applied board configuration and Klipper connection. Compatibility is unknown.'}[result['state']]
    return result
