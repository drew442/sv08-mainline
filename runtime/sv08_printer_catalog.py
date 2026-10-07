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
    if not isinstance(value,dict):raise ValueError('Object required; inspect structural fields')
    unknown=set(value)-set(allowed);missing=set(required)-set(value)
    if unknown or missing:
        detail='; '.join(label+': '+', '.join(str(k) for k in sorted(names,key=str)) for label,names in [('unsupported',unknown),('missing',missing)] if names)
        raise ValueError('Unsupported fields or missing structural fields — '+detail)


from sv08_printer_fields import FIELDS, LEGACY_FIELDS, ELECTRICAL, CHOICES


class Catalog:
    def __init__(self, path, diagnostic=False):
        self.data = strict_json(Path(path).read_bytes(), 512 * 1024)
        self.supported=True
        try:self.validate_catalog()
        except (ValueError,KeyError,TypeError):
            if not diagnostic:raise
            self.supported=False
            self.revision=digest(self.data);self.boards={};self.curves={};self.kinds={}
            return
        self.revision = digest(self.data)
        self.boards = {b['id']: b for b in self.data['boards']}
        self.curves = {c['id']: c for c in self.data['curves']}
        self.kinds = self.data['kinds']

    def validate_catalog(self):
        keys(self.data, ('format_version','boards','curves','kinds','factory'), ('format_version','boards','curves','kinds'))
        if self.data['format_version'] != 1 or type(self.data['format_version']) is not int:
            raise ValueError('Unsupported catalog schema')
        if not set(LEGACY_FIELDS)<=set(self.data['kinds']) or set(self.data['kinds'])-set(FIELDS):
            raise ValueError('New device kinds require a generator extension')
        for kind,fields in self.data['kinds'].items():
            if not isinstance(fields,dict) or any(FIELDS[kind].get(k)!=v for k,v in fields.items()) or not set(LEGACY_FIELDS.get(kind,FIELDS[kind]))<=set(fields):
                raise ValueError('Catalog field changes require a generator extension')
        types={t for fields in FIELDS.values() for t in fields.values()}|{'step','dir','enable','uart'}
        for fields in self.data['kinds'].values():
            if not isinstance(fields,dict) or not fields or any(not NAME.fullmatch(k) or t not in types for k,t in fields.items()):
                raise ValueError('Invalid catalog field schema')
        ids=set()
        for b in self.data['boards']:
            if not isinstance(b,dict) or not {'id','role','signals','motors','connectors','channel_counts','source','sharing_rules'} <= set(b):
                raise ValueError('Incomplete board catalog schema')
            if not isinstance(b['id'],str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,79}',b['id']) or b['id'] in ids or b['role'] not in ('main','tool','chamber'):
                raise ValueError('Invalid or duplicate catalog board')
            ids.add(b['id']);self.source(b['source'])
            if 'supported_transports' in b and (not isinstance(b['supported_transports'],list) or not b['supported_transports'] or any(t not in ('serial','can') for t in b['supported_transports']) or len(set(b['supported_transports'])) != len(b['supported_transports'])):
                raise ValueError('Invalid supported MCU transports')
            if b['sharing_rules'] != []:
                raise ValueError('Pin sharing requires an explicit code extension')
            if not isinstance(b['signals'],dict) or not b['signals']:
                raise ValueError('Empty signal catalog')
            for pin,signal in b['signals'].items():
                if not re.fullmatch(r'P[A-Z][0-9]{1,2}',pin):raise ValueError('Catalog needs canonical MCU GPIO names')
                if type(signal.get('reserved')) is not bool or not isinstance(signal.get('capabilities'),list) or not signal['capabilities'] or set(signal['capabilities'])-{'adc','heater','fan','probe','input','output','step','dir','enable','uart'}:
                    raise ValueError('Invalid signal capabilities or reservation')
                if type(signal['source'].get('line')) is not int or signal['source']['line'] < 1:
                    raise ValueError('Selectable signal needs exact primary source line')
            for connector in b['connectors'].values():
                pin=connector['pin'];cap=connector['capability']
                if pin not in b['signals'] or cap not in b['signals'][pin]['capabilities']:
                    raise ValueError('Connector capability does not match signal')
            for pins in b['motors'].values():
                if set(pins)!= {'step','dir','enable','uart'}:raise ValueError('Motor bundle requires step/dir/enable and addressed UART')
                for cap,pin in pins.items():
                    if pin not in b['signals'] or cap not in b['signals'][pin]['capabilities']:raise ValueError('Motor channel capability mismatch')
            for cap,count in b['channel_counts'].items():
                if type(count) is not int or count != sum(cap in s['capabilities'] for s in b['signals'].values()):
                    raise ValueError('Evidenced channel count mismatch')
            if any(pin in b['signals'] and not b['signals'][pin]['reserved'] for pin in b.get('reserved_pins',{})):
                raise ValueError('Reserved transport pin cannot be selectable')
        ids=set()
        factory={'sovol-hotend':('sv08_factory_hotend',11500,[[25,110000],[100,7008],[220,435]]),'sovol-bed':('sv08_factory_bed',4700,[[25,100000],[50,18085.4],[100,5362.6]])}
        for c in self.data['curves']:
            if c['id'] in ids:raise ValueError('Duplicate curve identifier')
            ids.add(c['id']);self.source(c['source']);self.number(c['reference_pullup'],'positive')
            if c['id'] in factory:
                expected=factory[c['id']]
                if c.get('reference_bounds') != ([5,305] if c['id']=='sovol-hotend' else [5,105]):
                    raise ValueError('Fixed vendor configured temperature bounds changed')
                if (c['sensor_type'],c['reference_pullup'],c['points']) != expected:
                    raise ValueError('Fixed vendor DEFAULT thermal definition changed')
            elif c['points'] is not None or c['sensor_type'] not in ('Generic 3950','EPCOS 100K B57560G104F','ATC Semitec 104GT-2','PT1000'):
                raise ValueError('Only sourced fixed factory custom thermistors are supported')
            if c.get('limits') is not None:
                if not isinstance(c['limits'],list) or len(c['limits'])!=2:raise ValueError('Invalid component limits')
                for value in c['limits']:self.number(value,'number')
                if c['limits'][0]>=c['limits'][1]:raise ValueError('Invalid component limits')
        if not set(factory)<=ids:raise ValueError('Factory DEFAULT definitions are required')
        if 'factory' in self.data:
            from sv08_printer_fields import validate_printer_settings
            keys(self.data['factory'],('printer_settings','source'),('printer_settings','source'))
            self.source(self.data['factory']['source']);validate_printer_settings(self.data['factory']['printer_settings'],self)
        # Existing kinds may acquire data-only reference bundles. Validate the
        # same bounded typed draft and exclusive resources as user-entered data.
        self.boards = {b['id']: b for b in self.data['boards']}
        self.curves = {c['id']: c for c in self.data['curves']}
        self.kinds = self.data['kinds']
        for board in self.boards.values():
            preset_ids = set()
            if not isinstance(board.get('presets',[]),list) or len(board.get('presets',[]))>64:
                raise ValueError('At most 64 declarative reference presets per board')
            for preset in board.get('presets', []):
                keys(preset, ('id','label','notes','devices'), ('id','label','notes','devices'))
                if not isinstance(preset['id'],str) or not NAME.fullmatch(preset['id']) or preset['id'] in preset_ids:
                    raise ValueError('Invalid or duplicate reference preset')
                preset_ids.add(preset['id'])
                if not all(isinstance(preset[k],str) and 0 < len(preset[k]) <= 2000 for k in ('label','notes')):
                    raise ValueError('Reference preset needs bounded labels and uncertainty notes')
                if not isinstance(preset['devices'],list) or not 1 <= len(preset['devices']) <= 64:
                    raise ValueError('Invalid preset dependency bundle')
                for device in preset['devices']:
                    keys(device, ('name','kind','settings','sources'), ('name','kind','settings','sources'))
                    if device['kind'] not in self.kinds or not isinstance(device['sources'],dict) or set(device['sources']) != set(device['settings']):
                        raise ValueError('Every reference default needs field provenance')
                    if 'current_rating_rms' in device['settings'] or 'z_offset' in device['settings']:
                        raise ValueError('Physical motor rating and calibrated probe offset cannot be reference defaults')
                    for source in device['sources'].values():
                        self.source({**board['source'], **source})
                        if type(source.get('line')) is not int or source['line'] < 1 or not {'option','section','value','transform'} <= set(source):
                            raise ValueError('Reference defaults need exact source option/line and transformation')
                        if source['transform'] not in ('number','pin','invert','pullup','curve','text','software-default','connector','association','boolean','alias','sensorless','firmware-spi','firmware-default','print-fan-role','starting-value'):
                            raise ValueError('Unsupported reference default transformation')
                self.apply_preset(dict(format_version=1,boards={board['role']:{'id':board['id']}},devices=[],geometry={}), board['role'], preset['id'])

    def apply_preset(self, draft, role, preset_id):
        self.validate(draft)
        board = self.board(draft, role)
        preset = next((p for p in board.get('presets',[]) if p['id'] == preset_id), None)
        if preset is None:
            raise ValueError('Unknown reference preset for selected board')
        result = strict_json(encoded(draft))
        # Append atomically; do not overwrite, silently rename or merge a sensor
        # dependency with an existing user selection. Validation refuses collisions.
        result['devices'] += [dict(name=d['name'],kind=d['kind'],board=role,settings=strict_json(encoded(d['settings']))) for d in preset['devices']]
        self.validate(result)
        return result

    def select_component(self, draft, role, preset_id):
        """Replace a named assembly atomically, retaining unrelated selections.

        Existing calibration belongs to the removed assembly, not its replacement.
        Validation still refuses incompatible pins and external dependencies.
        """
        self.validate(draft)
        board = self.board(draft, role)
        preset = next((p for p in board.get('presets', []) if p['id'] == preset_id), None)
        if preset is None:
            raise ValueError('Unknown component for selected board')
        names = {d['name'] for d in preset['devices']}
        if any(d['name'] in names and d['board'] != role for d in draft['devices']):
            raise ValueError('Component name belongs to another board')
        # Legacy standalone temperature checks may use different names for the
        # same physical input. Selecting its assembly replaces that sensor too,
        # but must never remove a sensor used by a retained heater.
        sensor_pins = {d['settings'].get('pin') for d in preset['devices'] if d['kind'] == 'sensor'}
        replaced = names | {d['name'] for d in draft['devices']
                            if d['board'] == role and d['kind'] == 'sensor'
                            and d['settings'].get('pin') in sensor_pins}
        if any(d['name'] not in replaced and d['settings'].get('sensor') in replaced
               for d in draft['devices']):
            raise ValueError('Component sensor is used by another heater')
        result = strict_json(encoded(draft))
        result['devices'] = [d for d in result['devices'] if d['name'] not in replaced]
        result = self.apply_preset(result, role, preset_id)
        for device in result['devices']:
            if device['name'] in names:
                device['profile'] = preset_id
                for key in ('pid_kp', 'pid_ki', 'pid_kd'):
                    device['settings'].pop(key, None)
        self.validate(result)
        return result

    @staticmethod
    def source(source):
        if not isinstance(source,dict) or not {'path','revision','accessed'} <= set(source):raise ValueError('Catalog provenance required')
        if not isinstance(source['path'],str) or not source['path'].startswith(('upstream/', 'catalog/printer/sources/')) or '..' in source['path'].split('/'):
            raise ValueError('Invalid primary source path')
        if not re.fullmatch(r'[0-9a-f]{40}',source['revision']) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',source['accessed']):
            raise ValueError('Catalog requires exact revision and access date')

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
        if not self.supported:raise ValueError('Unsupported catalog; export draft for diagnosis')
        if len(encoded(draft)) > DRAFT_LIMIT:
            raise ValueError('Draft exceeds 128 KiB')
        keys(draft, ('format_version', 'boards', 'devices', 'geometry', 'definition_plan', 'custom_config'), ('format_version', 'boards', 'devices', 'geometry'))
        if type(draft['format_version']) is not int or draft['format_version'] != 1:
            raise ValueError('Unsupported draft schema; original retained')
        if 'custom_config' in draft:
            if not isinstance(draft['custom_config'], str) or len(draft['custom_config'].encode())>65536:raise ValueError('Custom configuration exceeds 64 KiB')
            from sv08_printer_publish import sections
            custom_sections=sections(draft['custom_config'])
            if any(s.startswith('include ') for s in custom_sections):raise ValueError('Custom includes require managed closure adoption')
        if 'definition_plan' in draft:
            from sv08_printer_compose import validate_plan
            validate_plan(draft['definition_plan'], self)
        keys(draft['boards'], ('main', 'tool', 'chamber'))
        for role, selection in draft['boards'].items():
            keys(selection, ('id', 'transport', 'identity', 'reference_ack'))
            if 'id' in selection:
                self.board(draft, role)
            if 'transport' in selection and selection['transport'] not in ('serial', 'can'):
                raise ValueError('Unsupported MCU transport')
            if selection.get('transport') and 'id' in selection and selection['transport'] not in self.board(draft,role).get('supported_transports', ['serial','can']):
                raise ValueError('Unsupported transport for selected board')
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
        keys(draft['geometry'], (*GEOMETRY,'square_corner_velocity'))
        for v in draft['geometry'].values():
            self.number(v, 'positive')
        if not isinstance(draft['devices'], list) or len(draft['devices']) > 64:
            raise ValueError('At most 64 connected devices are supported')
        used, names = {}, set()
        for device in draft['devices']:
            keys(device, ('name', 'board', 'kind', 'settings', 'profile'), ('name', 'board', 'kind', 'settings'))
            name, kind, role = device['name'], device['kind'], device['board']
            if not isinstance(name, str) or not NAME.fullmatch(name) or name in names:
                raise ValueError('Device names must be unique simple lowercase names')
            names.add(name)
            if kind not in self.kinds or role not in ('main', 'tool', 'chamber'):
                raise ValueError('Unknown device kind or board role')
            board = self.board(draft, role)
            if kind == 'chamber' and (role != 'chamber' or name != 'chamber_temp' or device['settings'].get('control','watermark') != 'watermark'):
                raise ValueError('Chamber module requires its own board and watermark heater reference')
            if 'profile' in device and not any(p['id'] == device['profile'] and any(d['name'] == name and d['kind'] == kind for d in p['devices']) for p in board.get('presets', [])):
                raise ValueError('Unknown component profile for this board/device')
            settings = device['settings']; keys(settings, self.kinds[kind])
            def allocate(pin, cap):
                self.pin(board, pin, cap)
                resource = (role, pin)
                if resource in used:
                    raise ValueError('Pin collision: ' + role + ':' + pin)
                used[resource] = name
            for field, value in settings.items():
                typ = self.kinds[kind][field]
                if typ in ELECTRICAL and typ!='motor':
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
                elif typ == 'thermistor_points':
                    if self.curves.get(settings.get('curve'), {}).get('sensor_type') == 'PT1000':
                        raise ValueError('PT1000 uses its platinum definition, not a custom NTC curve')
                    if not isinstance(value, list) or len(value) != 3:
                        raise ValueError('Custom NTC curve requires three temperature/resistance pairs')
                    for point in value:
                        if not isinstance(point, list) or len(point) != 2:
                            raise ValueError('Custom curve requires temperature/resistance pairs')
                        self.number(point[0], 'number'); self.number(point[1], 'positive')
                        if point[0] <= -273.15:
                            raise ValueError('Custom curve temperatures must exceed absolute zero')
                    if not all(value[i][0] < value[i+1][0] and value[i][1] > value[i+1][1] for i in (0, 1)):
                        raise ValueError('NTC curve needs increasing temperatures and decreasing resistances')
                    # Check coefficients using the pinned upstream three-point math.
                    # Runtime installs do not include upstream sources; coefficient
                    # checks below duplicate only the documented three-point math.
                    inv = [1. / (p[0] + 273.15) for p in value]
                    logs = [math.log(p[1]) for p in value]
                    if abs(sum(logs)) < 1.e-12:
                        raise ValueError('Custom curve has degenerate resistance coefficients')
                    g2 = (inv[1]-inv[0]) / (logs[1]-logs[0])
                    g3 = (inv[2]-inv[0]) / (logs[2]-logs[0])
                    c = (g3-g2) / (logs[2]-logs[1]) / sum(logs)
                    b = g2-c*(logs[0]**2+logs[0]*logs[1]+logs[1]**2)
                    if c <= 0:  # Upstream falls back to the outer-point beta curve.
                        b = (inv[2]-inv[0]) / (logs[2]-logs[0])
                    if not math.isfinite(b) or not math.isfinite(c) or b <= 0:
                        raise ValueError('Custom curve has invalid Steinhart-Hart coefficients')
                elif typ == 'ratio':
                    if not isinstance(value,str) or len(value)>120 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?:[0-9]+(?:\.[0-9]+)?(?:,[0-9]+(?:\.[0-9]+)?:[0-9]+(?:\.[0-9]+)?)*',value) or any(float(n)<=0 for pair in value.split(',') for n in pair.split(':')):
                        raise ValueError('Gear ratio needs positive numeric upstream pairs')
                elif typ == 'boolean':
                    if type(value) is not bool:
                        raise ValueError('Polarity and digital pull-up need explicit Boolean values')
                elif typ == 'name':
                    if not isinstance(value, str) or not NAME.fullmatch(value):
                        raise ValueError('Invalid sensor association')
                elif typ in CHOICES:
                    if value not in CHOICES[typ]:raise ValueError('Unsupported '+typ)
                elif typ == 'control':
                    if value not in ('pid', 'watermark'):
                        raise ValueError('Unsupported heater control')
                else:
                    self.number(value, typ)
            if 'min_temp' in settings and settings['min_temp'] <= -273.15:
                raise ValueError('Temperature bound must be above absolute zero')
            if 'microsteps' in settings and settings['microsteps'] not in (1,2,4,8,16,32,64,128,256):
                raise ValueError('Microsteps must be a supported power of two')
            if 'min_temp' in settings and 'max_temp' in settings:
                if settings['min_temp'] >= settings['max_temp']:
                    raise ValueError('Temperature minimum must be below maximum')
                curve = self.curves.get(settings.get('curve'))
                if curve and curve.get('limits') and not (curve['limits'][0] <= settings['min_temp'] < settings['max_temp'] <= curve['limits'][1]):
                    raise ValueError('Temperatures exceed documented component limits')
            if kind=='output' and settings.get('pwm') and settings.get('cycle_time',.1)>3:raise ValueError('Mainline PWM cycle must be at most 3 seconds')
            if settings.get('verify_max_error',120)>120 or settings.get('verify_check_gain_time',120)>120 or settings.get('verify_hysteresis',10)>10:raise ValueError('Heater verification exceeds supported protection bounds')
            if settings.get('endstop_mode')=='sensorless' and ('homing_retract_dist' in settings and settings['homing_retract_dist']!=0):raise ValueError('Sensorless homing needs an explicit threshold and zero retract')
            if 'run_current' in settings and 'current_rating_rms' in settings and settings['run_current'] > settings['current_rating_rms']:
                raise ValueError('RMS driver current exceeds owner-entered motor RMS rating')
            # Pinned tmc2209 selects tmc2130.TMCCurrentHelper (MAX_CURRENT).
            # A software parser limit, never a physical safe-current rating.
            if settings.get('run_current', 0) > 2.000:
                raise ValueError(name + '.run_current: pinned TMC2209 software maximum is 2.000 A; physical rating remains unverified')
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
        if typ in ('nonnegative','nonnegative_integer','byte','unit_interval') and value<0:raise ValueError('Value must be nonnegative')
        if typ in ('byte','unit_interval') and value>(255 if typ=='byte' else 1):raise ValueError('Value exceeds supported range')
        if typ in ('positive', 'integer') and value <= 0:
            raise ValueError('Value must be positive')
        if typ == 'fraction' and not 0 < value <= 1:
            raise ValueError('Power fraction must be above zero and at most one')
        if typ in ('integer','address','byte','nonnegative_integer') and type(value) is not int:
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
