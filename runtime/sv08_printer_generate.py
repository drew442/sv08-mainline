"""Deterministic inactive configs. Sensor mode is a dedicated positive allowlist."""
from sv08_printer_catalog import BUNDLE_LIMIT, GEOMETRY

GENERATOR_VERSION = 5


def generate(catalog, draft, mode):
    catalog.validate(draft)
    if mode not in ('sensors', 'full'):
        raise ValueError('Choose sensors or full inactive SV08 candidate')
    blockers = []
    def require(settings, fields, label):
        for field in fields:
            if field not in settings:
                blockers.append(label + '.' + field + ': required for ' + mode)
    for role, board in draft['boards'].items():
        require(board, ('id', 'transport', 'identity', 'reference_ack'), role)
        if board.get('reference_ack') is not True:
            blockers.append(role + ': explicitly acknowledge provisional reference mapping')
    if 'main' not in draft['boards']:
        blockers.append('main: choose the primary Klipper MCU board and transport')
    sensors = {d['name']: d for d in draft['devices'] if d['kind'] == 'sensor'}
    for d in draft['devices']:
        s, kind, name = d['settings'], d['kind'], d['name']
        if kind == 'sensor':
            require(s, [k for k in catalog.kinds[kind] if k != 'custom_curve'], name)
        elif kind == 'input':
            require(s, catalog.kinds[kind], name)
        elif mode == 'sensors':
            blockers.append(name + ': output-bearing device is not allowed in sensor mode')
        elif kind in ('motor', 'extruder'):
            fields = ['connector','invert_dir','invert_enable','microsteps','rotation_distance','run_current','current_rating_rms','sense_resistor','uart_address']
            if name in ('stepper_x','stepper_y'):
                fields += ['position_min','position_max','position_endstop','homing_speed','endstop_pin','endstop_invert','endstop_pullup']
            elif name == 'stepper_z':
                fields += ['position_min','position_max','homing_speed']
            if kind == 'extruder':
                fields += ['pin','invert','sensor','max_power','control','nozzle_diameter','filament_diameter','min_extrude_temp']
            require(s, fields, name)
        elif kind in ('probe','fan'):
            require(s, catalog.kinds[kind], name)
        elif kind in ('bed','chamber'):
            require(s, ('pin','invert','sensor','max_power','control'), name)
            if kind == 'chamber':require(s, ('max_delta',), name)
        if mode == 'full' and kind in ('bed','extruder') and s.get('control') == 'pid':
            require(s, ('pid_kp','pid_ki','pid_kd'), name)
    if mode == 'sensors' and not sensors:
        blockers.append('Choose at least one temperature sensor')
    if mode == 'full':
        require(draft['geometry'], GEOMETRY, 'geometry')
        required = {'stepper_x':'motor','stepper_y':'motor','stepper_z':'motor','stepper_z1':'motor','stepper_z2':'motor','stepper_z3':'motor','extruder':'extruder','heater_bed':'bed','probe':'probe'}
        actual = {d['name']: d['kind'] for d in draft['devices']}
        for name, kind in required.items():
            if actual.get(name) != kind:
                blockers.append(name + ': required ' + kind + ' for CoreXY/four-Z')
        for d in draft['devices']:
            if d['kind'] in ('motor','extruder','bed','probe') and d['name'] not in required:
                blockers.append(d['name'] + ': unsupported full SV08 section name')
            s = d['settings']
            if d['name'] in ('stepper_x','stepper_y') and all(k in s for k in ('position_min','position_max','position_endstop')):
                if not s['position_min'] <= s['position_endstop'] <= s['position_max']:
                    blockers.append(d['name'] + ': endstop outside axis bounds')
            if d['kind'] == 'extruder' and s.get('sensor') in sensors:
                bounds = sensors[s['sensor']]['settings']
                if 'min_extrude_temp' in s and 'max_temp' in bounds and not 0 < s['min_extrude_temp'] < bounds['max_temp']:
                    blockers.append('extruder.min_extrude_temp: must retain cold extrusion protection below max_temp')
    if blockers:
        return dict(complete=False, blockers=blockers, warnings=[], text=None)
    lines = ['# Provisional inactive candidate. Software syntax is not hardware validation.',
             '# Sensor/circuit identity, ratings, polarity and commissioning require physical checks.']
    def section(name, values):
        lines.extend(['', '[' + name + ']'])
        for key, value in values.items():
            lines.append(key + ': ' + (str(value).lower() if type(value) is bool else str(value)))
    def qualified(role, pin):
        return (role+':' if role != 'main' else '') + pin
    def digital(d, field='pin', invert='invert', pull='digital_pullup'):
        s=d['settings']
        return ('^' if s.get(pull) else '') + ('!' if s.get(invert) else '') + qualified(d['board'], s[field])
    for role, b in sorted(draft['boards'].items()):
        section('mcu' + (' '+role if role != 'main' else ''), {'canbus_uuid' if b['transport']=='can' else 'serial': b['identity']})
    section('printer', {'kinematics':'none','max_velocity':1,'max_accel':1} if mode=='sensors' else {'kinematics':'corexy',**draft['geometry']})
    for cid in sorted({d['settings']['curve'] for d in sensors.values()}):
        c = catalog.curves[cid]
        if c['points']:
            values={}
            for i,(t,r) in enumerate(c['points'],1):values.update({f'temperature{i}':t,f'resistance{i}':r})
            section('thermistor '+c['sensor_type'], values)
    for name, d in sorted(sensors.items()):
        if 'custom_curve' in d['settings']:
            values = {}
            for i, (t, r) in enumerate(d['settings']['custom_curve'], 1):
                values.update({f'temperature{i}': t, f'resistance{i}': r})
            section('thermistor sv08_custom_' + name, values)
    heater_sensors = {d['settings']['sensor'] for d in draft['devices'] if mode=='full' and d['kind'] in ('bed','extruder','chamber')}
    def thermal(d):
        s=d['settings'];c=catalog.curves[s['curve']]
        return dict(sensor_type='sv08_custom_'+d['name'] if 'custom_curve' in s else c['sensor_type'], sensor_pin=qualified(d['board'], s['pin']), pullup_resistor=s['pullup_resistor'], min_temp=s['min_temp'],max_temp=s['max_temp'])
    def heater_values(d):
        s = d['settings']
        values = thermal(sensors[s['sensor']])
        values.update(heater_pin=digital(d), max_power=s['max_power'], control=s['control'])
        if d['kind'] == 'chamber':values.update(gcode_id='C',max_delta=s['max_delta'])
        if s['control'] == 'pid':
            values.update({k:s[k] for k in ('pid_kp','pid_ki','pid_kd')})
        return values
    for d in sorted(draft['devices'],key=lambda d:d['name']):
        name, kind, s = d['name'], d['kind'], d['settings']
        if kind=='sensor':
            if name not in heater_sensors:section('temperature_sensor '+name, thermal(d))
        elif kind=='input':
            section('filament_switch_sensor '+name,dict(switch_pin=digital(d),pause_on_runout=False))
        elif mode=='full':
            if kind in ('motor','extruder'):
                motor=catalog.board(draft,d['board'])['motors'][s['connector']]
                values={k+'_pin':('!' if s.get('invert_'+k) else '')+qualified(d['board'],motor[k]) for k in ('step','dir','enable')}
                values.update({k:s[k] for k in ('microsteps','rotation_distance')})
                if 'gear_ratio' in s:values['gear_ratio']=s['gear_ratio']
                if name in ('stepper_x','stepper_y','stepper_z'):
                    values.update({k:s[k] for k in ('position_min','position_max','homing_speed')})
                    if name=='stepper_z':values['endstop_pin']='probe:z_virtual_endstop'
                    else:values.update(position_endstop=s['position_endstop'],endstop_pin=digital(d,'endstop_pin','endstop_invert','endstop_pullup'))
                if kind=='extruder':
                    values.update({k:s[k] for k in ('nozzle_diameter','filament_diameter','min_extrude_temp')})
                    values.update(heater_values(d))
                section(name,values)
                section('tmc2209 '+name, {**{'uart_pin':qualified(d['board'],motor['uart'])},**{k:s[k] for k in ('run_current','sense_resistor','uart_address')}})
            elif kind=='bed':section(name,heater_values(d))
            elif kind=='chamber':section('heater_generic '+name,heater_values(d))
            elif kind=='fan':section('fan_generic '+name,dict(pin=digital(d),max_power=s['max_power']))
            elif kind=='probe':section('probe',{**{'pin':digital(d)},**{k:s[k] for k in ('x_offset','y_offset','z_offset')}})
    text='\n'.join(lines)+'\n'
    if len(text.encode())>BUNDLE_LIMIT:raise ValueError('Generated bundle exceeds 512 KiB')
    warnings=['Reference configuration only. Installed match and physical limits remain unverified.', 'Configured polarity is not measured polarity. TMC2209 2.000 A is a pinned software maximum, not a safe electrical rating.', 'Candidate saved separately; commissioning and activation require their own reviewed steps.']
    if mode == 'full':
        warnings.append('Before H06, compose once with the separately reviewed test-sv08-01-print-controls.cfg after the persistent gcodes directory exists. Controls and activation remain separate.')
    warnings += [(d['name'] + ': owner-entered custom NTC curve; calibration remains unverified') if 'custom_curve' in d['settings'] else catalog.curves[d['settings']['curve']]['origin'] for d in sensors.values()]
    return dict(complete=True, blockers=[], warnings=warnings, text=text)
