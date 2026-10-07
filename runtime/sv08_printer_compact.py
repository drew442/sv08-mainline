"""Compact author data -> validated, frozen public records. Never execute config."""
import copy
import re
from sv08_printer_catalog import keys, digest, NAME
from sv08_printer_definitions import builtins, validate_definition, bounded, FORMAT, MAX_DEPTH
from sv08_printer_fields import ELECTRICAL

ALIASES = {'sv08.factory.hotbed': 'sv08-main.bed_assembly',
           'sv08.factory.hotend': 'sv08-tool.hotend_assembly',
           'sv08.factory.mainboard': 'sv08-main.board',
           'sv08.factory.toolhead_board': 'sv08-tool.board',
           'sv08.factory.printer': 'sv08.factory'}
# The complete finite set of sections emitted by the managed generator.
SECTIONS = {'heater_bed': 'bed', 'extruder': 'extruder', 'probe': 'probe',
            'stepper': 'motor', 'fan_generic': 'fan', 'heater_generic': 'chamber',
            'filament_switch_sensor': 'input', 'temperature_sensor': 'sensor',
            'heater_fan': 'heater_fan', 'output_pin': 'output', 'neopixel': 'neopixel',
            'display': 'display', 'adxl345': 'accelerometer', 'gcode_button': 'pressure_switch'}
META = ('format_version','id','name','version','description','category','extends','configuration',
        'board','guide','license','aliases','hardware','sources','requires','advanced')
ADVANCED = ('components','connections','mapping','behaviours','inputs','dependencies',
            'conflicts','printer_settings','calibration','unresolved','compatibility')
CATEGORY = {'bed':'bed','extruder':'toolhead','sensor':'toolhead','motor':'motion',
            'probe':'probe','pressure_switch':'probe','input':'filament','fan':'cooling',
            'heater_fan':'cooling','chamber':'cooling','accelerometer':'toolhead'}
GROUPS = ('printer','bed_mesh','quad_gantry_level','safe_z_home')


def compact(d):
    return isinstance(d, dict) and 'kind' not in d


def section_kind(section):
    prefix, _, name = section.partition(' ')
    if section.startswith('stepper_') and ' ' not in section:return 'motor',section
    if prefix in ('extruder','heater_bed','probe','display') and not name:return SECTIONS[prefix],prefix
    if prefix == 'adxl345':return 'accelerometer',name or 'adxl345'
    if prefix not in SECTIONS or not name:raise ValueError('Unsupported compact Klipper section: '+section)
    if not NAME.fullmatch(name):raise ValueError('Invalid compact component name: '+name)
    return SECTIONS[prefix],name


def compile_records(records, catalog):
    """Resolve only this fetched commit plus named factory records; freeze the result."""
    factory={d['id']:d for d in builtins(catalog)}
    aliases={**{'sv08.factory.'+k.split('.',1)[1]:k for k in factory if k != 'sv08.factory'},**ALIASES}
    originals={d['id']:d for d in records}
    if len(originals)!=len(records):raise ValueError('Duplicate definition ID')
    done={};visiting=set();errors={}
    def compile_id(ident, depth=0):
        if depth>MAX_DEPTH or ident in visiting:raise ValueError('Compact inheritance cycle or depth exceeds 12')
        if ident in done:return done[ident]
        if ident not in originals:raise ValueError('Unknown compact inheritance base: '+ident)
        visiting.add(ident)
        try:
            raw=originals[ident]
            if not compact(raw):validate_definition(raw,catalog);result=copy.deepcopy(raw)
            else:
                refs=raw.get('extends',[]);refs=[refs] if isinstance(refs,str) else refs
                if not isinstance(refs,list) or not all(isinstance(r,str) for r in refs):raise ValueError('extends must be a name or list of names')
                bases=[]
                for ref in refs:
                    if ref in originals:bases.append(compile_id(ref,depth+1))
                    else:
                        key=aliases.get(ref,ref)
                        if key not in factory:raise ValueError('Unknown compact inheritance base: '+ref)
                        bases.append(factory[key])
                result=expand(raw,bases,catalog,factory)
            done[ident]=result;return result
        finally:visiting.remove(ident)
    for ident in originals:
        try:compile_id(ident)
        except (ValueError,KeyError,TypeError) as error:errors[ident]=str(error)
    return [done[d['id']] for d in records if d['id'] not in errors],errors


def expand(raw, bases, catalog, factory):
    bounded(raw)
    direct={k:v for k,v in raw.items() if k not in META}
    keys(raw,(*META,*direct),('id','name','version'))
    if raw.get('format_version','compact-1') != 'compact-1':raise ValueError('Unsupported compact format; use compact-1 or omit format_version')
    result=dict(format_version=FORMAT,id=raw['id'],name=raw['name'],version=raw['version'],kind='assembly',
                category=raw.get('category',bases[0]['category'] if bases else 'boards'),
                hardware=copy.deepcopy(raw.get('hardware',dict(product=raw['name'],revision='Author has not specified a physical hardware revision'))),
                compatibility=dict(requires_capabilities=['klipper.settings.v1']),sources=[],
                license=raw.get('license',bases[0]['license'] if bases else 'GPL-3.0-or-later'))
    base_ids=[]
    seen=set()
    def merge(base):
        ident=base['id']+'@'+base['version']
        if ident in seen:return
        seen.add(ident);base_ids.append(dict(id=base['id'],version=base['version'],sha256=digest(base)))
        for dependency in base.get('dependencies',[]):
            # Factory whole-printer inheritance includes exact documented boards/devices.
            if dependency.get('source')!='builtin':raise ValueError('Inherited external dependencies require an explicit advanced dependency, not implicit flattening')
            child=factory.get(dependency['id'])
            if child is None or child['version']!=dependency['version'] or digest(child)!=dependency['sha256']:raise ValueError('Factory inheritance dependency changed')
            if child['kind']=='board':
                dest=result.setdefault('dependencies',[])
                if dependency not in dest:dest.append(copy.deepcopy(dependency))
            else:merge(child)
        if base['kind']=='board':
            if 'mapping' in result and result['mapping']!=base['mapping']:raise ValueError('Combine board definitions using advanced dependencies, not multiple mappings')
            result['mapping']=copy.deepcopy(base['mapping'])
        for field in ('components','connections','behaviours','sources','calibration','unresolved'):
            for value in base.get(field,[]):
                dest=result.setdefault(field,[])
                if value not in dest:dest.append(copy.deepcopy(value))
        for field in ('inputs','printer_settings'):
            if field in base:result.setdefault(field,{}).update(copy.deepcopy(base[field]))
        for field in ('boards','printers','unknown'):
            for item in base.get('compatibility',{}).get(field,[]):
                values=result['compatibility'].setdefault(field,[])
                if item not in values:values.append(copy.deepcopy(item))
        if base.get('compatibility',{}).get('requires_capabilities'):
            result['compatibility']['requires_capabilities']=sorted(set(result['compatibility']['requires_capabilities'])|set(base['compatibility']['requires_capabilities']))
    for base in bases:merge(base)
    if 'mapping' in result:
        result['kind']='board'
        if result.get('components'):raise ValueError('Board and component bundles use explicit advanced dependencies')
    if not raw.get('category') and not bases:result['category']='boards'
    if 'description' in raw:result['description']=raw['description']
    if 'aliases' in raw:result['aliases']=copy.deepcopy(raw['aliases'])
    if 'requires' in raw:
        if not isinstance(raw['requires'],list):raise ValueError('requires must be a capability list')
        result['compatibility']['requires_capabilities']+=raw['requires']
    if 'sources' in raw:
        if not isinstance(raw['sources'],list):raise ValueError('sources must be an array')
        result['sources']+=copy.deepcopy(raw['sources'])
    guide=raw.get('guide')
    if guide is not None and (not isinstance(guide,str) or not guide.startswith('https://')):raise ValueError('guide must be an HTTPS URL')
    result['sources'].append(dict(id='compact-author',revision=digest(raw),locator='Author-declared compact modification; configuration claims are not measured hardware facts',**({'url':guide} if guide else {})))
    configuration=raw.get('configuration',{})
    if not isinstance(configuration,dict):raise ValueError('configuration must be an object of Klipper sections')
    if set(configuration)&set(direct):raise ValueError('Compact section supplied twice')
    configuration={**configuration,**direct}
    if 'mapping' in result and configuration:raise ValueError('Board definitions configure an advanced documented mapping, not hardware sections')
    for section,values in configuration.items():
        if not isinstance(values,dict):raise ValueError(section+': settings object required')
        if section in GROUPS:
            group='geometry' if section=='printer' else section
            values=copy.deepcopy(values)
            if section=='printer' and values.pop('kinematics','corexy')!='corexy':raise ValueError('Original SV08 uses corexy')
            result.setdefault('printer_settings',{}).setdefault(group,{}).update(values);continue
        if section.startswith('verify_heater '):
            name=section.split(' ',1)[1];c=next((c for c in result.get('components',[]) if c['name']==name and c['kind'] in ('bed','extruder')),None)
            if c is None:raise ValueError('verify_heater requires an included heater')
            keys(values,('max_error','check_gain_time','hysteresis','heating_gain'))
            c['settings'].update({'verify_'+k:v for k,v in values.items()});continue
        if section.startswith('tmc2209 '):
            name=section.split(' ',1)[1];c=next((c for c in result.get('components',[]) if c['name']==name and c['kind'] in ('motor','extruder')),None)
            if c is None:raise ValueError('tmc2209 requires an included motor')
            apply_settings(c,values,result,catalog,driver=True);continue
        kind,name=section_kind(section)
        if kind=='sensor' and values.get('sensor_type')=='temperature_mcu':kind='mcu_temperature'
        components=result.setdefault('components',[])
        matches=[c for c in components if c['name']==name]
        if len(matches)>1:raise ValueError('Ambiguous compact component role: '+name)
        if matches:
            c=matches[0]
            if c['kind']!=kind:raise ValueError('Compact section kind conflicts with inherited component')
        else:
            role=values.get('board',raw.get('board'))
            board_id=role if role in catalog.boards else None
            role=catalog.boards[board_id]['role'] if board_id else role
            if role not in ('main','tool','chamber'):raise ValueError(section+': new component needs an explicit board role or board ID')
            c=dict(name=name,kind=kind,board=role,settings={},endpoints={});components.append(c)
            if board_id:c['_board_id']=board_id
            if not bases and not raw.get('category'):result['category']=CATEGORY.get(kind,'boards')
        apply_settings(c,values,result,catalog)
    advanced=raw.get('advanced',{})
    if not isinstance(advanced,dict):raise ValueError('advanced must be an object')
    keys(advanced,ADVANCED)
    for field,value in advanced.items():
        if field in ('components','connections','behaviours','dependencies','conflicts'):
            if not isinstance(value,list):raise ValueError('advanced.'+field+': array required')
            result.setdefault(field,[]).extend(copy.deepcopy(value))
        elif field in ('inputs','printer_settings'):
            result.setdefault(field,{}).update(copy.deepcopy(value))
        else:result[field]=copy.deepcopy(value)
    if 'mapping' in result:result['kind']='board'
    elif result.get('behaviours') and not result.get('components') and not result.get('dependencies'):result['kind']='behaviour'
    # Author form and expansion/base identity are retained for inspection, never rerun.
    result['extensions']={'sv08.compact':dict(author=copy.deepcopy(raw),bases=base_ids)}
    for c in result.get('components',[]):c.pop('_board_id',None)
    validate_definition(result,catalog)
    for c in result.get('components',[]):
        settings=c['settings']
        if 'min_temp' in settings and 'max_temp' in settings and settings['min_temp']>=settings['max_temp']:raise ValueError(c['name']+': min_temp must be below max_temp')
    return result


def bind(c,field,value,result,catalog):
    """Resolve explicit connector names or exact documented pins; never borrow pins."""
    role=c['board'];cap=catalog.kinds[c['kind']][field]
    if not isinstance(value,str):raise ValueError(field+': connector or documented pin string required')
    board_id=c.get('_board_id') or (result.get('mapping',{}).get('id') if result.get('mapping',{}).get('role')==role else None)
    boards=[b for b in catalog.boards.values() if b['role']==role and (not board_id or b['id']==board_id)]
    if not board_id:
        # Existing endpoints pin the exact documented board scope when inherited.
        endpoints=c['endpoints'];old=next((x for x in result.get('connections',[]) if x['endpoint']==endpoints.get(field)),None)
        if old:boards=[b for b in boards if b['id'] in old['board_ids']]
        else:raise ValueError(field+': new connection requires an explicit documented board ID')
    invert=False;pullup=False
    while value and value[0] in '!^':
        if value[0]=='!':invert=not invert
        else:pullup=True
        value=value[1:]
    if ':' in value:
        selected,value=value.split(':',1)
        if selected not in (role,'mcu' if role=='main' else role):raise ValueError('Pin MCU role differs from component board')
    matches=[]
    for board in boards:
        mapping=board['motors'] if cap=='motor' else board['connectors']
        for name,conn in mapping.items():
            if (cap=='motor' and name==value) or cap!='motor' and conn['capability']==cap and (name==value or conn['pin']==value):matches.append((board['id'],name))
    names={name for _,name in matches}
    if len(names)!=1:raise ValueError(field+': connection is missing or ambiguous in the documented board mapping')
    if cap=='motor' and (invert or pullup):raise ValueError('Motor connector takes a plain documented connector name')
    if pullup and c['kind'] not in ('input','probe','pressure_switch'):raise ValueError('Pullup prefix is unsupported for this connection')
    endpoint=c['name']+'.'+field;c['endpoints'][field]=endpoint
    result['connections']=[x for x in result.get('connections',[]) if x['endpoint']!=endpoint]
    result['connections'].append(dict(endpoint=endpoint,board=role,connector=next(iter(names)),capability=cap,board_ids=sorted({b for b,_ in matches}),contact=None))
    if field in ('pin','endstop_pin'):
        if c['kind'] not in ('sensor','neopixel','accelerometer','display'):
            c['settings']['endstop_invert' if field=='endstop_pin' else 'invert']=invert
        elif invert:raise ValueError('Inversion unsupported for this connection')
        if c['kind'] in ('input','probe','pressure_switch'):c['settings']['digital_pullup']=pullup
        elif field=='endstop_pin':c['settings']['endstop_pullup']=pullup


def apply_settings(c, values, result, catalog, driver=False):
    kind=c['kind'];fields=catalog.kinds[kind]
    aliases={'heater_pin':'pin','switch_pin':'pin','sensor_type':'curve','driver_SGTHRS':'driver_sgthrs',
             'spi_software_miso_pin':'miso_pin','spi_software_mosi_pin':'mosi_pin','spi_software_sclk_pin':'sclk_pin'}
    forbidden=('pid_kp','pid_ki','pid_kd','z_offset','current_rating_rms','custom_curve')
    driver_fields={'run_current','sense_resistor','uart_address','interpolate','stealthchop_threshold','driver_sgthrs'}
    motor_pins={k:values[k+'_pin'] for k in ('step','dir','enable','uart') if k+'_pin' in values}
    if motor_pins:
        if kind not in ('motor','extruder'):raise ValueError('Motor pins require a motor/extruder component')
        endpoint=c['endpoints'].get('connector');binding=next((x for x in result.get('connections',[]) if x['endpoint']==endpoint),None)
        scope=binding['board_ids'] if binding else [c.get('_board_id')]
        matches=[]
        for board_id in scope:
            board=catalog.boards.get(board_id)
            if board is None:raise ValueError('Motor pin mapping requires an exact documented board')
            for connector,pins in board['motors'].items():
                ok=True
                for field,pin in motor_pins.items():
                    if not isinstance(pin,str) or not pin:raise ValueError('Motor pin string required')
                    bare=pin.removeprefix('!');parts=bare.split(':')
                    if len(parts)>2 or len(parts)==2 and parts[0] not in (c['board'],'mcu' if c['board']=='main' else c['board']):raise ValueError('Motor pin MCU role differs from component board')
                    if pins.get(field)!=parts[-1]:ok=False
                    if pin.startswith('!') and field not in ('dir','enable'):raise ValueError('Motor inversion is only supported for direction/enable')
                if ok:matches.append(connector)
        if len(set(matches))!=1:raise ValueError('Motor pins do not identify one documented connector')
        if binding and next(iter(set(matches)))!=binding['connector'] and len(motor_pins)<4:raise ValueError('Changing motor connector requires all four documented pins')
        bind(c,'connector',next(iter(set(matches))),result,catalog)
        for field in ('dir','enable'):
            if field in motor_pins:c['settings']['invert_'+field]=motor_pins[field].startswith('!')
    for option,value in values.items():
        if option in ('step_pin','dir_pin','enable_pin','uart_pin'):continue
        if kind=='display' and option=='lcd_type':
            if value!='uc1701':raise ValueError('Only the documented uc1701 display is supported')
            continue
        if kind=='display' and option=='encoder_pins':
            if not isinstance(value,str) or len(value.split(','))!=2:raise ValueError('encoder_pins needs two documented pins')
            pins=[v.strip() for v in value.split(',')]
            if any('!' in v for v in pins) or pins[0].startswith('^')!=pins[1].startswith('^'):raise ValueError('Unsupported encoder inversion/mixed pullups')
            c['settings']['encoder_pullup']=pins[0].startswith('^')
            for field,pin in zip(('encoder_a','encoder_b'),pins):bind(c,field,pin.removeprefix('^'),result,catalog)
            continue
        if kind=='display' and option=='click_pin':
            if not isinstance(value,str):raise ValueError('click_pin needs a documented pin')
            c['settings']['click_pullup']='^' in value[:2];c['settings']['click_invert']='!' in value[:2]
            bind(c,'click_pin',value.lstrip('^!'),result,catalog);continue
        if kind=='mcu_temperature' and option in ('sensor_type','sensor_mcu'):
            expected='temperature_mcu' if option=='sensor_type' else ('mcu' if c['board']=='main' else c['board'])
            if value!=expected:raise ValueError('MCU sensor type/role conflicts with component board')
            continue
        if option=='board':
            if value not in (c['board'],c.get('_board_id')):raise ValueError('Changing inherited board needs an explicit new component/mapping')
            continue
        field=aliases.get(option,option)
        if field.lower() in forbidden:raise ValueError(option+': instance calibration/rating belongs to local advanced settings, not published defaults')
        if driver and field not in driver_fields:raise ValueError('Unsupported compact TMC2209 setting: '+option)
        if option in ('sensor_pin','sensor_type','pullup_resistor','min_temp','max_temp') and kind in ('bed','extruder','chamber'):
            sensor=next((x for x in result['components'] if x['name']==c['settings'].get('sensor') and x['kind']=='sensor'),None)
            if sensor is None:
                sensor=dict(name=c['name']+'_sensor',kind='sensor',board=c['board'],settings={},endpoints={})
                if '_board_id' in c:sensor['_board_id']=c['_board_id']
                result['components'].append(sensor);c['settings']['sensor']=sensor['name']
            apply_settings(sensor,{'pin' if option=='sensor_pin' else option:value},result,catalog);continue
        if field not in fields:raise ValueError('Unsupported compact '+kind+' setting: '+option)
        if fields[field] in ELECTRICAL:bind(c,field,value,result,catalog);continue
        if field=='curve':
            if value in catalog.curves:curve=value
            else:
                matches=[cid for cid,curve in catalog.curves.items() if curve['sensor_type']==value]
                if len(matches)!=1:raise ValueError('Unknown or ambiguous sensor_type; use a supported sensor name or exact curve ID')
                curve=matches[0]
            c['settings']['curve']=curve
        else:c['settings'][field]=copy.deepcopy(value)
