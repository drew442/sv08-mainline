"""Data-only printer reference catalog and bounded typed drafts.

Original catalog-to-Klipper gap adapter; retire when upstream offers structured
hardware configuration, retaining export migration and negative fixtures.
"""
import hashlib
import json
import math
from pathlib import Path
import re

DRAFT_LIMIT = 128 * 1024
BUNDLE_LIMIT = 512 * 1024
NAME = re.compile(r'[a-z][a-z0-9_]{0,39}\Z')
GEOMETRY = ('max_velocity', 'max_accel', 'max_z_velocity', 'max_z_accel')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def strict_json(raw, limit=DRAFT_LIMIT):
    if len(raw) > limit:
        raise ValueError('Structured input exceeds 128 KiB')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
    except (RecursionError, UnicodeError, json.JSONDecodeError):
        raise ValueError('Invalid structured JSON') from None


def keys(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError('Unsupported fields or missing structural fields')


class Catalog:
    def __init__(self, path):
        self.data = strict_json(Path(path).read_bytes(), 512 * 1024)
        if self.data['format_version'] != 1:
            raise ValueError('Unsupported catalog schema')
        self.revision = digest(self.data)
        self.boards = {b['id']: b for b in self.data['boards']}
        self.curves = {c['id']: c for c in self.data['curves']}
        self.kinds = self.data['kinds']

    def board(self, draft, role):
        selection = draft['boards'].get(role, {})
        board = self.boards.get(selection.get('id'))
        if board is None or board['role'] != role:
            raise ValueError('Choose a documented board for ' + role)
        return board

    def pin(self, board, value, capability):
        # No aliases, embedded polarity, prefixes or user-generated raw config.
        signal = board['signals'].get(value)
        if not signal or signal['reserved'] or capability not in signal['capabilities']:
            raise ValueError('Pin is unavailable for the selected device role')
        return value

    def validate(self, draft):
        if len(encoded(draft)) > DRAFT_LIMIT:
            raise ValueError('Draft exceeds 128 KiB')
        keys(draft, ('format_version', 'boards', 'devices', 'geometry'), ('format_version', 'boards', 'devices', 'geometry'))
        if type(draft['format_version']) is not int or draft['format_version'] != 1:
            raise ValueError('Unsupported draft schema; original retained')
        keys(draft['boards'], ('main', 'tool'))
        for role, selection in draft['boards'].items():
            keys(selection, ('id', 'transport', 'identity', 'reference_ack'))
            if 'id' in selection:
                self.board(draft, role)
            if 'transport' in selection and selection['transport'] not in ('serial', 'can'):
                raise ValueError('Unsupported MCU transport')
            if 'identity' in selection:
                identity = selection['identity']
                if not isinstance(identity, str) or len(identity) > 240:
                    raise ValueError('Invalid private MCU identity')
                if selection.get('transport') == 'can':
                    if not re.fullmatch(r'[0-9a-f]{12}', identity):
                        raise ValueError('CAN UUID requires twelve lowercase hex digits')
                elif not re.fullmatch(r'/dev/(?:serial/by-id/)?[A-Za-z0-9_.-]+', identity):
                    raise ValueError('Serial identity requires a single documented /dev path')
            if 'reference_ack' in selection and type(selection['reference_ack']) is not bool:
                raise ValueError('Reference acknowledgment must be explicit')
        keys(draft['geometry'], GEOMETRY)
        for v in draft['geometry'].values():
            self.number(v, 'positive')
        if not isinstance(draft['devices'], list) or len(draft['devices']) > 64:
            raise ValueError('At most 64 connected devices are supported')
        used, names = {}, set()
        for device in draft['devices']:
            keys(device, ('name', 'board', 'kind', 'settings'), ('name', 'board', 'kind', 'settings'))
            name, kind, role = device['name'], device['kind'], device['board']
            if not isinstance(name, str) or not NAME.fullmatch(name) or name in names:
                raise ValueError('Device names must be unique simple lowercase names')
            names.add(name)
            if kind not in self.kinds or role not in ('main', 'tool'):
                raise ValueError('Unknown device kind or board role')
            board = self.board(draft, role)
            settings = device['settings']; keys(settings, self.kinds[kind])
            def allocate(pin, cap):
                self.pin(board, pin, cap)
                resource = (role, pin)
                if resource in used:
                    raise ValueError('Pin collision: ' + role + ':' + pin)
                used[resource] = name
            for field, value in settings.items():
                typ = self.kinds[kind][field]
                if typ in ('adc', 'heater', 'fan', 'probe', 'input'):
                    allocate(value, typ)
                elif typ == 'motor':
                    connector = board['motors'].get(value)
                    if connector is None:
                        raise ValueError('Unknown motor connector')
                    for cap, pin in connector.items():
                        allocate(pin, cap)
                    if 'uart' not in connector:
                        raise ValueError('Motor needs an evidenced TMC2209 UART channel')
                elif typ == 'curve':
                    if value not in self.curves:
                        raise ValueError('Unknown temperature curve')
                elif typ == 'boolean':
                    if type(value) is not bool:
                        raise ValueError('Polarity and digital pull-up need explicit Boolean values')
                elif typ == 'name':
                    if not isinstance(value, str) or not NAME.fullmatch(value):
                        raise ValueError('Invalid sensor association')
                elif typ == 'control':
                    if value not in ('pid', 'watermark'):
                        raise ValueError('Unsupported heater control')
                else:
                    self.number(value, typ)
            if 'min_temp' in settings and 'max_temp' in settings:
                if settings['min_temp'] >= settings['max_temp']:
                    raise ValueError('Temperature minimum must be below maximum')
                curve = self.curves.get(settings.get('curve'))
                if curve and curve.get('limits') and not (curve['limits'][0] <= settings['min_temp'] < settings['max_temp'] <= curve['limits'][1]):
                    raise ValueError('Temperatures exceed documented component limits')
            if 'run_current' in settings and 'current_rating_rms' in settings and settings['run_current'] > settings['current_rating_rms']:
                raise ValueError('RMS driver current exceeds owner-entered motor RMS rating')
            if 'position_min' in settings and 'position_max' in settings and settings['position_min'] >= settings['position_max']:
                raise ValueError('Axis minimum must be below maximum')
        heater_sensors = set()
        for device in draft['devices']:
            target = device['settings'].get('sensor')
            if target is not None:
                if target in heater_sensors:
                    raise ValueError('A sensor cannot be assigned to multiple heaters')
                heater_sensors.add(target)
            if target is not None and not any(d['name'] == target and d['kind'] == 'sensor' and d['board'] == device['board'] for d in draft['devices']):
                raise ValueError('Heater must reference a temperature sensor on its board')
        return draft

    @staticmethod
    def number(value, typ):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Numeric fields must be finite numbers')
        if typ in ('positive', 'integer') and value <= 0:
            raise ValueError('Value must be positive')
        if typ == 'fraction' and not 0 < value <= 1:
            raise ValueError('Power fraction must be above zero and at most one')
        if typ in ('integer', 'address') and type(value) is not int:
            raise ValueError('An integer is required')
        if typ == 'address' and not 0 <= value <= 3:
            raise ValueError('TMC2209 UART address must be 0 through 3')

    def change_board(self, draft, role, board_id):
        # Explicit caller confirmation; never translate connector indexes.
        result = strict_json(encoded(draft))
        result['boards'][role] = {'id': board_id}
        result['devices'] = [d for d in result['devices'] if d['board'] != role]
        self.validate(result)
        return result


def empty_draft():
    return dict(format_version=1, boards={}, devices=[], geometry={})
