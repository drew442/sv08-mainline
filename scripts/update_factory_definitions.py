#!/usr/bin/env python3
"""Reproduce sourced factory catalogue additions and public records; no printer access."""
import argparse,copy,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_fields import FIELDS

def update(source_root):
    path=source_root/'upstream/sovol-sv08/home/sovol/printer_data/config/printer.cfg'
    raw=path.read_bytes();expected='8936ceabc98a6583f3cff17093905162ac516a0996c8714ef62825a6cb005289'
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Pinned Sovol configuration changed; review source before regenerating')
    sections={};section=None;last_key=None
    for number,line in enumerate(raw.decode().splitlines(),1):
        if line.startswith('#*#'):break
        text=line.split('#',1)[0].strip()
        if text.startswith('[') and text.endswith(']'):section=text[1:-1];sections.setdefault(section,{});last_key=None
        elif section=='board_pins' and text.startswith('EXP'):
            value,line_number=sections[section]['aliases'];sections[section]['aliases']=(value+'\n'+text,line_number)
        elif section and re.match(r'^[a-zA-Z_][a-zA-Z_0-9]*\s*[:=]',text):
            key,value=re.split(r'\s*[:=]\s*',text,maxsplit=1);sections[section][key]=(value,number);last_key=key
        elif section and last_key and text:
            value,line_number=sections[section][last_key];sections[section][last_key]=(value+'\n'+text,line_number)
    c=json.loads((ROOT/'catalog/printer/catalog.json').read_text());c['kinds']=copy.deepcopy(FIELDS)
    boards={b['role']:b for b in c['boards'] if b['id'] in ('sv08-main','sv08-tool')}
    def source(role,section,key,transform='number',value=None):
        text,line=sections[section][key]
        return dict(line=line,section=section,option=key,value=text,transform=transform,reference='active reference' if value is None else value,reference_only=True)
    def put(device,role,field,section,key=None,transform='number',override=None):
        key=key or field;text,_=sections[section][key]
        typ=FIELDS[device['kind']][field]
        if override is not None:value=override
        elif transform=='pin':value=text.strip('^! ').split(':')[-1].strip()
        elif transform=='invert':value='!' in text
        elif transform=='pullup':value='^' in text
        elif typ=='boolean':value=text.lower()=='true'
        elif typ in ('name','color_order','samples_result','endstop_mode','ratio','control'):value=text
        else:value=float(text);value=int(value) if value.is_integer() else value
        if typ=='boolean' and transform=='number':transform='boolean'
        if field=='endstop_mode':transform='sensorless'
        device['settings'][field]=value;device['sources'][field]=source(role,section,key,transform)
    def derived(device,role,field,value,relative,needle,note):
        p=source_root/relative;lines=p.read_text().splitlines();line=next(i for i,s in enumerate(lines,1) if needle in s)
        revision='f0892d82b0f1c1228454f09eb508eddde2250f4b' if relative.startswith('upstream/klipper/') else 'a60644875f8c756d20b3828c9416518b414b5491'
        device['settings'][field]=value;device['sources'][field]=dict(path=relative,revision=revision,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),accessed='2026-10-06',line=line,section='upstream software default / explicit mainline adaptation',option=field,value=value,transform='firmware-spi' if relative.endswith('spi.c') else 'firmware-default' if 'sovol-sv08/' in relative else 'software-default',reference=note,reference_only=True)
    def device(name,kind):return dict(name=name,kind=kind,settings={},sources={})
    def add(role,ident,label,d,notes='Pinned factory configuration; identity and calibration remain local.'):
        board=boards[role];board['presets']=[p for p in board['presets'] if p['id']!=ident];board['presets'].append(dict(id=ident,label=label,notes=notes,devices=[d]))
    for role,board in boards.items():
        for preset in board['presets']:
            if preset['id']=='funssor_cn3d_bed':continue
            for d in preset['devices']:
                name=d['name'];kind=d['kind']
                if kind in ('motor','extruder'):
                    for field in ('interpolate','stealthchop_threshold'):
                        if field in sections['tmc2209 '+name]:put(d,role,field,'tmc2209 '+name)
                    if 'full_steps_per_rotation' in sections[name]:put(d,role,'full_steps_per_rotation',name)
                    if name in ('stepper_x','stepper_y'):
                        put(d,role,'endstop_mode',name,'endstop_pin','text','sensorless')
                        for field,transform in [('endstop_pin','pin'),('endstop_invert','invert'),('endstop_pullup','pullup')]:put(d,role,field,'tmc2209 '+name,'diag_pin',transform)
                        put(d,role,'driver_sgthrs','tmc2209 '+name)
                    for field in ('homing_retract_dist','homing_positive_dir','homing_retract_speed','second_homing_speed'):
                        if field in FIELDS[kind] and field in sections[name]:put(d,role,field,name)
                if kind in ('bed','extruder'):
                    for field in ('max_error','check_gain_time','hysteresis','heating_gain'):put(d,role,'verify_'+field,'verify_heater '+name,field)
                if kind=='probe':
                    for field in ('speed','samples','sample_retract_dist','lift_speed','samples_result','samples_tolerance','samples_tolerance_retries'):put(d,role,field,'probe',transform='text' if field=='samples_result' else 'number')
                    note=' The duplicate vendor probe speed entries resolve to the last active value, 5 mm/s. Probe Z calibration is not a factory default.'
                    preset['notes']=preset['notes'].replace(note,'')+note
                if kind=='input':
                    for field in ('pause_on_runout','event_delay','pause_delay'):put(d,role,field,'filament_switch_sensor filament_sensor')
    d=device('hotend_fan','heater_fan')
    for field in ('pin','invert'):put(d,'tool',field,'heater_fan hotend_fan','pin','pin' if field=='pin' else 'invert')
    for field in ('max_power','kick_start_time','heater','heater_temp','tachometer_ppr','tachometer_poll_interval'):put(d,'tool',field,'heater_fan hotend_fan',transform='text' if field=='heater' else 'number')
    put(d,'tool','tachometer_pin','heater_fan hotend_fan',transform='pin');add('tool','hotend_fan','Factory hotend cooling fan with tachometer',d)
    d=device('pressure_switch','pressure_switch')
    for field,transform in [('pin','pin'),('invert','invert'),('digital_pullup','pullup')]:put(d,'main',field,'probe_pressure','pin',transform)
    add('main','pressure_switch','Factory nozzle-contact pressure input',d,'Source probe_pressure electrical input monitored with an empty-action mainline gcode_button. Proprietary pressure-probing and automatic Z-calibration workflows are separate; no probing/motion hook is installed.')
    for name in ('main_led','beeper'):
        d=device(name,'output');section='output_pin '+name
        for field,transform in [('pin','pin'),('invert','invert')]:put(d,'main',field,section,'pin',transform)
        # Vendor uses 1 for LED PWM and False for the beeper.
        put(d,'main','pwm',section,override=sections[section]['pwm'][0].lower() in ('true','1'))
        put(d,'main','value',section)
        derived(d,'main','shutdown_value',0,'upstream/klipper/klippy/extras/output_pin.py',"'shutdown_value', 0.",'Pinned upstream shutdown default; no physical rating inferred')
        if 'cycle_time' in sections[section] and float(sections[section]['cycle_time'][0])<=3:put(d,'main','cycle_time',section)
        else:derived(d,'main','cycle_time',.1,'upstream/klipper/klippy/extras/output_pin.py',"'cycle_time', 0.100",'Pinned mainline PWM default; vendor LED 5 s exceeds mainline 3 s maximum. Omitted for digital beeper.')
        if name=='beeper':d['sources']['pin']['transform']='alias'
        add('main',name,'Factory '+name.replace('_',' '),d,'Vendor LED PWM period 5 s exceeds the mainline maximum of 3 s; this definition uses the pinned upstream default 0.1 s.' if name=='main_led' else 'Digital beeper output; no audible startup action.')
    aliases=dict(re.findall(r'(EXP[12]_[0-9]+)=(P[A-Z][0-9]+)',sections['board_pins']['aliases'][0]))
    for board in boards.values():
        for p in board['presets']:
            for d in p['devices']:
                for key,src in d['sources'].items():
                    if src.get('transform')=='alias' and src['value'].lstrip('^!') in aliases:d['settings'][key]=aliases[src['value'].lstrip('^!')]
    d=device('display','display')
    for field,option in [('cs_pin','cs_pin'),('a0_pin','a0_pin'),('rst_pin','rst_pin'),('miso_pin','spi_software_miso_pin'),('mosi_pin','spi_software_mosi_pin'),('sclk_pin','spi_software_sclk_pin')]:put(d,'main',field,'display',option,'pin',aliases[sections['display'][option][0]])
    enc=sections['display']['encoder_pins'][0].split(',')
    for field,text in zip(('encoder_a','encoder_b'),enc):put(d,'main',field,'display','encoder_pins','pin',aliases[text.strip().lstrip('^!')])
    put(d,'main','encoder_pullup','display','encoder_pins','pullup');put(d,'main','click_pin','display','click_pin','pin',aliases[sections['display']['click_pin'][0].lstrip('^!')]);put(d,'main','click_pullup','display','click_pin','pullup');put(d,'main','click_invert','display','click_pin','invert');put(d,'main','contrast','display');add('main','display','Factory UC1701 display and controls',d)
    d=device('screen_colour','neopixel')
    put(d,'main','pin','neopixel Screen_Colour','pin','pin',aliases[sections['neopixel Screen_Colour']['pin'][0]])
    for field,option in [('chain_count','chain_count'),('color_order','color_order'),('initial_red','initial_RED'),('initial_green','initial_GREEN'),('initial_blue','initial_BLUE')]:put(d,'main',field,'neopixel Screen_Colour',option,transform='text' if field=='color_order' else 'number')
    add('main','screen_colour','Factory display lighting',d)
    d=device('adxl345','accelerometer');put(d,'tool','cs_pin','adxl345','cs_pin','pin')
    spi='upstream/sovol-sv08/home/sovol/klipper/src/stm32/spi.c'
    for field,value in [('miso_pin','PB14'),('mosi_pin','PB15'),('sclk_pin','PB13')]:derived(d,'tool',field,value,spi,'BUS_PINS_spi2','Vendor spi2 is enumeration 0/default; explicitly bind the same wires for mainline software SPI')
    derived(d,'tool','spi_speed',5000000,'upstream/sovol-sv08/home/sovol/klipper/klippy/extras/adxl345.py','default_speed=5000000','Vendor driver configured SPI rate, not an inferred MCU clock')
    add('tool','adxl345','Factory ADXL345 accelerometer',d)
    for role,name,section in [('main','mcu_temp','temperature_sensor mcu_temp'),('tool','toolhead_temp','temperature_sensor Toolhead_Temp')]:
        d=device(name,'mcu_temperature')
        for field in ('min_temp','max_temp'):
            if field in sections[section]:put(d,role,field,section)
        add(role,name,'Factory '+role+' controller temperature',d)
    for board in boards.values():
        for preset in board['presets']:
            for d in preset['devices']:
                for key,src in d['sources'].items():
                    if src.get('transform')=='pin' and 'EXP' in str(src['value']):src['transform']='alias'
    # Every added electrical binding has an explicit reference connector and pin.
    for role,board in boards.items():
        for preset in board['presets']:
            if preset['id']=='funssor_cn3d_bed':continue
            for d in preset['devices']:
                for field,value in d['settings'].items():
                    cap=FIELDS[d['kind']][field]
                    if cap not in ('input','output','fan','probe','adc','heater'):continue
                    src=d['sources'][field];src['reference_only']=True;signal=board['signals'].get(value)
                    if signal is None:board['signals'][value]=dict(capabilities=[cap],reserved=False,source={**board['source'],**src},evidence='documented-reference')
                    elif cap not in signal['capabilities']:raise ValueError('Existing pin capability conflict: '+value)
                    else:signal['source']={**board['source'],**src}
                    if not any(x['pin']==value and x['capability']==cap for x in board['connectors'].values()):board['connectors'][d['name']+'_'+field]=dict(label=d['name'].replace('_',' ')+' '+field.replace('_',' '),pin=value,capability=cap,contact=None,source={**board['source'],**src},evidence='Source-qualified logical connection')
        board['channel_counts']={cap:sum(cap in s['capabilities'] for s in board['signals'].values()) for cap in sorted({cap for s in board['signals'].values() for cap in s['capabilities']})}
    def process(section):
        result={}
        for key,(text,line) in sections[section].items():
            if key in ('gantry_corners','points'):result[key]=[[float(v) for v in row.split(',')] for row in text.strip().splitlines()]
            elif key in ('mesh_min','mesh_max','probe_count','mesh_pps'):result[key]=[float(v) for v in text.split(',')] if key in ('mesh_min','mesh_max') else [int(v) for v in text.split(',')]
            elif key=='algorithm':result[key]=text
            else:result[key]=float(text) if key!='retries' else int(text)
        return result
    c['factory']={'printer_settings':{'geometry':{k:float(sections['printer'][k][0]) for k in ('max_velocity','max_accel','max_z_velocity','max_z_accel','square_corner_velocity')},'bed_mesh':process('bed_mesh'),'quad_gantry_level':process('quad_gantry_level'),'safe_z_home':dict(home_xy_position=[191,165],speed=60,z_hop=10,z_hop_speed=15)},'source':copy.deepcopy(boards['main']['source'])}
    def json_numbers(value):
        if isinstance(value,dict):return {k:json_numbers(v) for k,v in value.items()}
        if isinstance(value,list):return [json_numbers(v) for v in value]
        if type(value) is float and value.is_integer():return int(value)
        return value
    c['factory']=json_numbers(c['factory'])
    (ROOT/'catalog/printer/catalog.json').write_text(json.dumps(c,indent=2)+'\n')
    from sv08_printer_catalog import Catalog
    from sv08_printer_definitions import builtins
    records=builtins(Catalog(ROOT/'catalog/printer/catalog.json'))
    (ROOT/'catalog/printer/definitions/builtin.json').write_text(json.dumps(dict(format_version='0.1',records=records),indent=2)+'\n')
    print('Factory public records:',len(records))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);args=parser.parse_args();update(args.source_root)
