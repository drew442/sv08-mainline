"""Deterministic inactive configs. Sensor mode is a dedicated positive allowlist."""
from sv08_printer_catalog import BUNDLE_LIMIT, GEOMETRY
from sv08_printer_fields import LEGACY_FIELDS

GENERATOR_VERSION = 8


def generate(catalog, draft, mode):
    from sv08_printer_compose import locked_catalog, apply_inputs
    draft=apply_inputs(draft,catalog)
    catalog=locked_catalog(draft,catalog)
    catalog.validate(draft)
    import copy
    draft=copy.deepcopy(draft)
    source_draft=copy.deepcopy(draft)
    setup_requirements=[]
    calibration_pending=False
    if mode in ('setup','full'):
        for device in draft['devices']:
            settings=device['settings']
            if device['kind']=='probe' and 'z_offset' not in settings:
                start=settings.get('z_offset_start')
                # Compatibility for previously saved, locked factory definitions.
                # Sovol a606448 printer.cfg line71 comments the starting value 0;
                # the SAVE_CONFIG value 1.0 is measured and is never imported.
                if start is None and device['name']=='probe' and device['board']=='tool' and draft['boards'].get('tool',{}).get('id')=='sv08-tool' and settings.get('pin')=='PB6' and settings.get('x_offset')==-17 and settings.get('y_offset')==10:
                    start=0
                if start is not None:
                    settings['z_offset']=start
                    calibration_pending=True
                    setup_requirements.append('probe.z_offset: calibration pending; sourced factory starting value '+str(start)+' mm is used, not a measured offset')
            if mode=='setup' and device['kind'] in ('bed','extruder') and settings.get('control')=='pid' and not all(k in settings for k in ('pid_kp','pid_ki','pid_kd')):
                settings['control']='watermark'
                setup_requirements.append(device['name']+': setup uses Klipper watermark control until local PID gains are recorded')
    if mode not in ('sensors', 'setup', 'full'):
        raise ValueError('Choose sensors, setup or full inactive SV08 candidate')
    blockers = []
    policies={};closure={};printer_settings={};documented_devices=[]
    if 'definition_plan' in draft:
        from sv08_printer_compose import validate_plan, connection_devices
        closure,policies=validate_plan(draft['definition_plan'],catalog)
        for ident,definition in sorted(closure.items()):
            for group,values in definition.get('printer_settings',{}).items():
                if group in printer_settings and printer_settings[group]!=values:raise ValueError('Conflicting printer settings ownership')
                printer_settings[group]=values
            try:documented_devices.extend(connection_devices(definition,draft,catalog))
            except ValueError as error:blockers.append(ident+': '+str(error))
            for component in definition.get('components',[]):
                if not any(d['name']==component['name'] and d['board']==component['board'] and d['kind']==component['kind'] for d in draft['devices']):blockers.append(ident+': definition contribution removed — '+component['name'])
            for gap in definition.get('unresolved',[]):blockers.append(ident+': definition incomplete — '+gap)
            for key,inp in definition.get('inputs',{}).items():
                if not inp.get('required'):continue
                device,field=inp['target'].split('.',1)
                actual=next((d for d in draft['devices'] if d['name']==device),None)
                supplied=actual and field in actual['settings'] or field in draft['boards'].get(device,{}) or inp['target'] in draft['definition_plan'].get('instance_values',{})
                if not supplied:blockers.append(ident+': needs your input — '+inp['label'])
        if policies and mode=='sensors':blockers.append('Behaviour outputs require full mode; sensor mode remains output-free')

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
    if draft.get('custom_config') and mode=='sensors':blockers.append('Custom configuration requires full mode; sensor allowlist unchanged')
    sensors = {d['name']: d for d in draft['devices'] if d['kind'] == 'sensor'}
    for d in draft['devices']:
        s, kind, name = d['settings'], d['kind'], d['name']
        if kind == 'sensor':
            require(s, [k for k in catalog.kinds[kind] if k != 'custom_curve'], name)
        elif kind == 'input':
            require(s, LEGACY_FIELDS[kind], name)
        elif mode == 'sensors':
            blockers.append(name + ': output-bearing device is not allowed in sensor mode')
        elif kind in ('motor', 'extruder'):
            fields = ['connector','invert_dir','invert_enable','microsteps','rotation_distance','run_current','sense_resistor','uart_address']
            if name in ('stepper_x','stepper_y'):
                fields += ['position_min','position_max','position_endstop','homing_speed','endstop_pin','endstop_invert','endstop_pullup']
            elif name == 'stepper_z':
                fields += ['position_min','position_max','homing_speed']
            if kind == 'extruder':
                fields += ['pin','invert','sensor','max_power','control','nozzle_diameter','filament_diameter','min_extrude_temp']
            documented=any(c['name']==name and c['kind']==kind and c['board']==d['board'] and c['settings'].get('run_current')==s.get('run_current') and c['settings'].get('connector')==s.get('connector') for c in documented_devices)
            if not documented:fields.append('current_rating_rms')
            if s.get('endstop_mode')=='sensorless':fields+=['driver_sgthrs','homing_retract_dist']
            require(s, fields, name)
        elif kind in ('probe','fan'):
            require(s, LEGACY_FIELDS[kind], name)
        elif kind in ('bed','chamber'):
            require(s, ('pin','invert','sensor','max_power','control'), name)
            if kind == 'chamber':require(s, ('max_delta',), name)
        elif kind not in ('sensor','input'):
            if kind=='heater_fan' and s.get('heater') and not any(x['name']==s['heater'] and x['kind'] in ('bed','extruder','chamber') for x in draft['devices']):blockers.append(name+': choose the controlled heater')
            require(s, [k for k in catalog.kinds[kind] if not (kind=='mcu_temperature' or kind=='output' and k=='cycle_time')], name)
        if mode in ('setup','full') and kind in ('bed','extruder') and s.get('control') == 'pid':
            require(s, ('pid_kp','pid_ki','pid_kd'), name)
    if mode == 'sensors' and not sensors:
        blockers.append('Choose at least one temperature sensor')
    if mode in ('setup','full'):
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
            if isinstance(value,list):
                value=('\n  '+'\n  '.join(', '.join(map(str,p)) for p in value)) if value and isinstance(value[0],list) else ', '.join(map(str,value))
            lines.append(key + ': ' + (str(value).lower() if type(value) is bool else str(value)))
    def qualified(role, pin):
        return (role+':' if role != 'main' else '') + pin
    def digital(d, field='pin', invert='invert', pull='digital_pullup'):
        s=d['settings']
        return ('^' if s.get(pull) else '') + ('!' if s.get(invert) else '') + qualified(d['board'], s[field])
    for role, b in sorted(draft['boards'].items()):
        section('mcu' + (' '+role if role != 'main' else ''), {'canbus_uuid' if b['transport']=='can' else 'serial': b['identity']})
    section('printer', {'kinematics':'none','max_velocity':1,'max_accel':1} if mode=='sensors' else {'kinematics':'corexy',**draft['geometry']})
    if mode in ('setup','full'):
        for group,values in sorted(printer_settings.items()):
            if group!='geometry':section(group,values)
        if any(d['kind']=='input' and d['settings'].get('pause_on_runout') for d in draft['devices']):section('pause_resume',{})
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
    heater_sensors = {d['settings']['sensor'] for d in draft['devices'] if mode in ('setup','full') and d['kind'] in ('bed','extruder','chamber')}
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
            section('filament_switch_sensor '+name,dict(switch_pin=digital(d),pause_on_runout=s.get('pause_on_runout',False) if mode in ('setup','full') else False,**{k:s[k] for k in ('event_delay','pause_delay') if k in s}))
        elif mode in ('setup','full'):
            if kind in ('motor','extruder'):
                motor=catalog.board(draft,d['board'])['motors'][s['connector']]
                values={k+'_pin':('!' if s.get('invert_'+k) else '')+qualified(d['board'],motor[k]) for k in ('step','dir','enable')}
                values.update({k:s[k] for k in ('microsteps','rotation_distance')})
                for k in ('gear_ratio','full_steps_per_rotation','homing_retract_dist','homing_positive_dir','homing_retract_speed','second_homing_speed'):
                    if k in s:values[k]=s[k]
                if name in ('stepper_x','stepper_y','stepper_z'):
                    values.update({k:s[k] for k in ('position_min','position_max','homing_speed')})
                    if name=='stepper_z':values['endstop_pin']='probe:z_virtual_endstop'
                    else:values.update(position_endstop=s['position_endstop'],endstop_pin='tmc2209_'+name+':virtual_endstop' if s.get('endstop_mode')=='sensorless' else digital(d,'endstop_pin','endstop_invert','endstop_pullup'))
                if kind=='extruder':
                    values.update({k:s[k] for k in ('nozzle_diameter','filament_diameter','min_extrude_temp')})
                    values.update(heater_values(d))
                section(name,values)
                driver={'uart_pin':qualified(d['board'],motor['uart']),**{k:s[k] for k in ('run_current','sense_resistor','uart_address')}}
                driver.update({k:s[k] for k in ('interpolate','stealthchop_threshold') if k in s})
                if s.get('endstop_mode')=='sensorless':driver.update(diag_pin=digital(d,'endstop_pin','endstop_invert','endstop_pullup'),driver_SGTHRS=s['driver_sgthrs'])
                section('tmc2209 '+name,driver)
            elif kind=='bed':section(name,heater_values(d))
            elif kind=='chamber':section('heater_generic '+name,heater_values(d))
            elif kind=='fan':section('fan_generic '+name,dict(pin=digital(d),max_power=s['max_power']))
            elif kind=='probe':section('probe',{**{'pin':digital(d)},**{k:s[k] for k in ('x_offset','y_offset','z_offset','speed','samples','sample_retract_dist','lift_speed','samples_result','samples_tolerance','samples_tolerance_retries') if k in s}})
            elif kind=='heater_fan':
                section('heater_fan '+name,dict(pin=digital(d),tachometer_pin=qualified(d['board'],s['tachometer_pin']),**{k:s[k] for k in ('max_power','kick_start_time','heater','heater_temp','tachometer_ppr','tachometer_poll_interval')}))
            elif kind=='output':
                section('output_pin '+name,dict(pin=digital(d),**{k:s[k] for k in ('pwm','value','shutdown_value')},**({'cycle_time':s['cycle_time']} if s['pwm'] and 'cycle_time' in s else {})))
            elif kind=='neopixel':
                section('neopixel '+name,dict(pin=qualified(d['board'],s['pin']),**{k:s[k] for k in ('chain_count','color_order','initial_red','initial_green','initial_blue')}))
            elif kind=='display':
                section('display',dict(lcd_type='uc1701',**{k:qualified(d['board'],s[k]) for k in ('cs_pin','a0_pin','rst_pin')},**{'spi_software_'+k+'_pin':qualified(d['board'],s[k+'_pin']) for k in ('miso','mosi','sclk')},encoder_pins=', '.join(('^' if s['encoder_pullup'] else '')+qualified(d['board'],s[k]) for k in ('encoder_a','encoder_b')),click_pin=digital(d,'click_pin','click_invert','click_pullup'),contrast=s['contrast']))
            elif kind=='accelerometer':
                section('adxl345'+(' '+name if name!='adxl345' else ''),dict(cs_pin=qualified(d['board'],s['cs_pin']),spi_speed=s['spi_speed'],**{'spi_software_'+k+'_pin':qualified(d['board'],s[k+'_pin']) for k in ('miso','mosi','sclk')}))
            elif kind=='mcu_temperature':section('temperature_sensor '+name,dict(sensor_type='temperature_mcu',sensor_mcu=d['board'] if d['board']!='main' else 'mcu',**s))
            elif kind=='pressure_switch':section('gcode_button '+name,dict(pin=digital(d),press_gcode='',release_gcode=''))
            if kind in ('extruder','bed') and any(k.startswith('verify_') for k in s):
                section('verify_heater '+name,{k:s['verify_'+k] for k in ('max_error','check_gain_time','hysteresis','heating_gain') if 'verify_'+k in s})
    text='\n'.join(lines)+'\n'
    if draft.get('custom_config'):
        from sv08_printer_publish import sections
        if sections(text)&sections(draft['custom_config']):raise ValueError('Custom configuration duplicates managed sections; transfer ownership before editing')
        text+='\n# Explicit user-owned configuration\n'+draft['custom_config']+'\n'
    if len(text.encode())>BUNDLE_LIMIT:raise ValueError('Generated bundle exceeds 512 KiB')
    warnings=['Reference configuration only. Installed match and physical limits remain unverified.', 'Configured polarity is not measured polarity. TMC2209 2.000 A is a pinned software maximum, not a safe electrical rating.', 'Candidate saved separately; commissioning and activation require their own reviewed steps.']
    if draft.get('custom_config'):warnings.append('User-owned custom code: structural validation only; review and commission any thermal/motion/startup effects separately.')
    if mode in ('setup','full'):
        warnings.append('Validate configured limits and complete component commissioning before starting the printer. Configuration application does not grant a printing release.')
    warnings += [(d['name'] + ': owner-entered custom NTC curve; calibration remains unverified') if 'custom_curve' in d['settings'] else catalog.curves[d['settings']['curve']]['origin'] for d in sensors.values()]
    behaviours=''
    if policies:
        # A finite check-only hook; no heating, cooling wait or homing side effect.
        # Threshold semantics are explicit; unsupported operations never approximate.
        behaviours='[gcode_macro SV08_LEVELLING_PRECONDITIONS]\ngcode:\n'
        for index,b in enumerate(policies['levelling.preconditions']):
            sensor=sensors.get(b['sensor'])
            if not sensor:raise ValueError('Levelling policy sensor is not selected')
            var='t'+str(index)
            conditions={'at_least':var+' < '+str(b['threshold']),'at_most':var+' > '+str(b['threshold']),'within_range':var+' < '+str(b['threshold'])+' or '+var+' > '+str(b.get('upper'))}
            thermal=next((d['name'] if d['kind']!='chamber' else 'heater_generic '+d['name'] for d in draft['devices'] if d['settings'].get('sensor')==b['sensor']), 'temperature_sensor '+b['sensor'])
            behaviours+='  {% set '+var+' = printer["'+thermal+'"].temperature %}\n  {% if '+conditions[b['comparison']]+' %}\n    { action_raise_error("Levelling temperature condition not satisfied") }\n  {% endif %}\n'
    if behaviours:text+='\n# Managed check-only behaviour hook\n'+behaviours
    if len(text.encode())>BUNDLE_LIMIT:raise ValueError('Generated bundle exceeds 512 KiB')
    if mode!='sensors':
        from sv08_printer_stack import support, files
        integration=support(draft,printer_settings,mode,policies,calibration_pending)
        from sv08_printer_publish import sections
        if sections(text)&sections(integration):raise ValueError('Custom configuration conflicts with managed print controls; explicit ownership review required')
        exported=files(text,integration,source_draft,mode,GENERATOR_VERSION,catalog.revision,calibration_pending)
        if sum(len(v.encode()) for v in exported.values())>BUNDLE_LIMIT:raise ValueError('Complete exported configuration exceeds 512 KiB')
        text+=integration
        if len(text.encode())>BUNDLE_LIMIT:raise ValueError('Generated bundle exceeds 512 KiB')
        return dict(complete=True,blockers=[],warnings=warnings+setup_requirements,text=text,behaviours=behaviours,files=exported,setup_requirements=setup_requirements,printing_enabled=mode=='full' and not calibration_pending)
    return dict(complete=True, blockers=[], warnings=warnings, text=text,behaviours=behaviours)
