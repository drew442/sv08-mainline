"""Pinned native SAVE_CONFIG contract, pure ownership and hardware-bound mirrors.

Only registered options enter the mutable top-level lane. Unknown autosave data
is an error, never an opaque record silently accepted as printing evidence.
"""
import argparse
import configparser
import copy
import hashlib
import importlib.util
import json
import os
import math
from pathlib import Path
import re

from sv08_printer_catalog import BUNDLE_LIMIT, digest, strict_json

KLIPPER_REVISION = 'f0892d82b0f1c1228454f09eb508eddde2250f4b'
CONFIGFILE_SHA256 = 'c4049b906b5341ad492105901515c6d9a4504d980098f9ce346df48388c53cf4'
KLIPPER_SOURCE = Path('/opt/sv08-mainline/klipper')
PROFILE_NAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}\Z')
MESH_FIELDS = {'version','points','min_x','max_x','min_y','max_y','x_count','y_count','mesh_x_pps','mesh_y_pps','algo','tension'}
SHAPER_FIELDS = {'shaper_type_x','shaper_type_y','shaper_freq_x','shaper_freq_y'}


def upstream(source=KLIPPER_SOURCE):
    """Use the unchanged pinned parser and native commenting algorithm."""
    path=Path(source)/'klippy/configfile.py';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CONFIGFILE_SHA256:raise ValueError('Unsupported Klipper config reader revision')
    spec=importlib.util.spec_from_file_location('_sv08_pinned_configfile',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def parse(text):
    if not isinstance(text,str) or len(text.encode())>BUNDLE_LIMIT:raise ValueError('Calibration configuration exceeds limit')
    parser=configparser.RawConfigParser(interpolation=None,strict=True)
    try:parser.read_string(text)
    except configparser.Error:raise ValueError('Ambiguous configuration section/option') from None
    return {s:dict(parser.items(s)) for s in parser.sections()}


def registry(config):
    result={}
    for section,options in config.items():
        fields=set()
        if section in ('probe','bltouch'):fields={'z_offset'}
        elif section in ('extruder','heater_bed') or section.startswith(('extruder_stepper ', 'heater_generic ')):
            if 'sensor_type' in options:fields={'control','pid_kp','pid_ki','pid_kd'}
        elif section in ('stepper_x','stepper_y','stepper_z') and 'position_endstop' in options:fields={'position_endstop'}
        elif section=='input_shaper':fields=SHAPER_FIELDS
        elif section=='bed_tilt':fields={'x_adjust','y_adjust','z_adjust'}
        elif section=='axis_twist_compensation':fields={'z_compensations','zy_compensations','compensation_start_x','compensation_end_x','compensation_start_y','compensation_end_y'}
        elif section.startswith('endstop_phase '):fields={'trigger_phase'}
        if fields:result[section]=fields
    return result


def allowed_fields(section, config):
    fields=registry(config).get(section)
    for prefix,module,options in [('bed_mesh ','bed_mesh',MESH_FIELDS),('skew_correction ','skew_correction',{'xy_skew','xz_skew','yz_skew'})]:
        if section.startswith(prefix) and module in config and PROFILE_NAME.fullmatch(section[len(prefix):]):return options
    return fields or set()


def validate_records(records, config):
    if len(records)>64:raise ValueError('Too many persisted calibration records')
    for section,options in records.items():
        allowed=allowed_fields(section,config)
        if not allowed or not options or set(options)-allowed:raise ValueError('Unsupported native calibration record: '+section)
        if (section in ('heater_bed','extruder') or section.startswith('heater_generic ')) and set(options)!={'control','pid_kp','pid_ki','pid_kd'}:raise ValueError('Incomplete persisted PID calibration record')
        for field,value in options.items():
            if not isinstance(value,str) or len(value)>65536:raise ValueError('Invalid native calibration value')
            if field=='control':
                if value!='pid':raise ValueError('Native calibrated heater control must be pid')
            elif field.startswith('shaper_type'):
                if value not in ('zv','mzv','zvd','ei','2hump_ei','3hump_ei'):raise ValueError('Unsupported persisted shaper type')
            elif field=='algo':
                if value not in ('lagrange','bicubic'):raise ValueError('Unsupported mesh algorithm')
            elif field=='trigger_phase':
                if not re.fullmatch(r'\d+/\d+',value) or not 0<=int(value.split('/')[0])<int(value.split('/')[1]):raise ValueError('Invalid endstop phase')
            else:
                parts=[x for x in re.split(r'[,\s]+',value.strip()) if x]
                try:values=[float(x) for x in parts]
                except ValueError:raise ValueError('Finite calibration numbers required') from None
                if not values or not all(math.isfinite(v) for v in values):raise ValueError('Finite calibration numbers required')
                if field not in ('points','z_compensations','zy_compensations') and len(values)!=1:raise ValueError('Scalar calibration field required')
                if field in ('pid_kp','pid_ki','pid_kd') and values[0]<=0:raise ValueError('PID gain must be positive')
                if field.startswith('shaper_freq') and values[0]<0:raise ValueError('Shaper frequency must be nonnegative (Hz)')
                if field.startswith('damping_ratio') and not 0<=values[0]<=1:raise ValueError('Invalid shaper damping ratio')
                if field in ('version','x_count','y_count','mesh_x_pps','mesh_y_pps') and (not values[0].is_integer() or not 0<=values[0]<=256):raise ValueError('Invalid mesh count/version')
        from sv08_printer_fields import validate_numeric_values
        validate_numeric_values('probe' if section in ('probe','bltouch') else 'motor' if section.startswith('stepper_') else section,{k:float(v) for k,v in options.items() if k in ('z_offset','position_endstop')})
        if section.startswith('bed_mesh '):
            if set(options)!=MESH_FIELDS or options['version']!='1':raise ValueError('Incomplete or unsupported mesh profile')
            rows=[[float(v) for v in row.split(',')] for row in options['points'].strip().splitlines()]
            if len(rows)!=int(options['y_count']) or any(len(row)!=int(options['x_count']) for row in rows):raise ValueError('Mesh profile dimensions disagree')
            if not float(options['min_x'])<float(options['max_x']) or not float(options['min_y'])<float(options['max_y']):raise ValueError('Mesh profile bounds disagree')
    return records


def split_lane(text):
    """Keep exact non-calibration lines immutable; move known options to root."""
    config=parse(text);known={s:allowed_fields(s,config) for s in config};immutable=[];lane={};section=None;moving=False
    profiles={s for s in config if s.startswith(('bed_mesh ','skew_correction ')) and known[s]}
    validate_records({s:config[s] for s in profiles},config)
    for line in text.splitlines(keepends=True):
        stripped=line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            section=stripped[1:-1];moving=False
            if section in profiles:continue
        match=re.match(r'^([A-Za-z0-9_]+)\s*[:=]',line)
        if match:
            field=match[1].lower();moving=field in known.get(section,set())
            if moving:lane.setdefault(section,{})[field]=config[section][field]
        if moving and (match or line[:1].isspace()):continue
        immutable.append(line)
    return ''.join(immutable),render(lane)


def render(records):
    return ''.join('\n['+s+']\n'+''.join(k+': '+v.replace('\n','\n  ')+'\n' for k,v in sorted(options.items())) for s,options in sorted(records.items()) if options)


def native_parts(raw, source=KLIPPER_SOURCE):
    module=upstream(source);native=object.__new__(module.ConfigAutoSave)
    regular,footer=native._find_autosave_data(raw)
    if '#*#' in raw and not footer:raise ValueError('Malformed native SAVE_CONFIG footer')
    records=parse(footer) if footer.strip() else {}
    return regular,records


def recognized_root(baseline, observed, config, source=KLIPPER_SOURCE):
    """Accept only exact upstream commenting/footer changes to a bound root."""
    module=upstream(source);native=object.__new__(module.ConfigAutoSave)
    base_regular,base_records=native_parts(baseline,source)
    regular,records=native_parts(observed,source)
    validate_records(base_records,config);validate_records(records,config)
    reader=module.ConfigFileReader();fileconfig=reader.build_fileconfig(render(records),'<native-calibration>')
    expected=native._strip_duplicates(base_regular,fileconfig)
    if regular.rstrip()!=expected.rstrip():raise ValueError('Unrecognized configuration root drift')
    # An unchanged active default must not shadow a supposedly persisted value.
    active=parse(regular)
    for section,options in records.items():
        if set(options)&set(active.get(section,{})):raise ValueError('Persisted calibration is shadowed by a root option')
    return records


def hardware_binding(draft):
    """Structural fingerprint excluding measurements; source snapshots stay pinned."""
    data=copy.deepcopy(draft);data.pop('native_calibration',None);data.pop('format_version',None)
    for device in data['devices']:
        for field in ('z_offset','pid_kp','pid_ki','pid_kd','position_endstop'):
            device['settings'].pop(field,None)
        if device['kind'] in ('bed','extruder','chamber'):device['settings'].pop('control',None)
    plan=data.get('definition_plan',{})
    plan.pop('instance_values',None)
    # Retaining immutable source history in the binding is conservative.
    return digest(data)


def inspect_envelope(value):
    expected={'format_version','revision','draft','current','previous'}
    if not isinstance(value,dict) or not expected<=set(value) or set(value)-expected-{'sources'}:raise ValueError('Unsupported configuration envelope shape')
    if value['format_version'] not in (1,2):raise ValueError('Unsupported stored schema; preserve original for a matching reader')
    return dict(format_version=value['format_version'],legacy=value['format_version']==1,native_calibration=value['draft'].get('native_calibration'),older_reader='opaque export/read only' if value['format_version']==2 else 'legacy reader supported')


def migrate_envelope(value):
    inspect_envelope(value);result=copy.deepcopy(value);result['format_version']=2
    return result


def main():
    parser=argparse.ArgumentParser(description='Offline version-bound printer state inspection/migration; preserves input')
    parser.add_argument('action',choices=('inspect','migrate'));parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();value=strict_json(args.input.read_bytes(),2*1024*1024)
    if args.action=='inspect':print(json.dumps(inspect_envelope(value),indent=2));return
    if args.output is None:parser.error('migrate requires a new --output file')
    result=migrate_envelope(value)
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(result,stream,indent=2);stream.write('\n')



def dependency_binding(config, section, sources=None):
    """Calibration dependencies, deliberately excluding unrelated fans/macros."""
    if section.startswith(('bed_mesh ','skew_correction ')) or section in ('probe','bltouch','bed_tilt','axis_twist_compensation') or section.startswith('endstop_phase '):
        names={s for s in config if s.startswith(('mcu','stepper_','tmc2209 ')) or s in ('printer','probe','bltouch','bed_mesh','bed_tilt','axis_twist_compensation','heater_bed','extruder','skew_correction')}
    elif section=='input_shaper':
        names={s for s in config if s.startswith(('mcu','stepper_','tmc2209 ','adxl345','resonance_tester')) or s in ('printer','input_shaper','extruder')}
    elif section in ('heater_bed','extruder') or section.startswith('heater_generic '):
        names={section}|{s for s in config if s.startswith(('mcu','thermistor '))}
    else:names={section}
    structural={s:{k:v for k,v in config[s].items() if k not in allowed_fields(s,config) and (s!='printer' or k=='kinematics')} for s in sorted(names) if s in config}
    return digest(dict(structural=structural,source=(sources or {}).get(calibration_group(section))))


def compatible_records(mirror, config, sources=None):
    if not mirror:return {}
    if not isinstance(mirror,dict) or set(mirror)-{'format_version','publication','context','records','bindings','status','origins'} or not {'format_version','publication','context','records','bindings'}<=set(mirror) or mirror['format_version']!=1:raise ValueError('Unsupported native calibration mirror')
    selected={s:copy.deepcopy(options) for s,options in mirror['records'].items() if allowed_fields(s,config) and mirror['bindings'].get(s)==dependency_binding(config,s,sources)}
    validate_records(selected,config)
    return selected


def apply_records(text, records):
    """Replace only explicitly registered option values, retaining other text."""
    config=parse(text);validate_records(records,config)
    chunks=re.split(r'(?m)(?=^\[)',text);seen=set();out=[]
    for chunk in chunks:
        match=re.match(r'^\[([^\]]+)\]',chunk)
        if not match or match[1] not in records:out.append(chunk);continue
        section=match[1];seen.add(section);options=records[section];lines=chunk.splitlines(keepends=True);remaining=set(options);body=[];skip=False
        for line in lines:
            found=re.match(r'^([A-Za-z0-9_]+)\s*[:=]',line)
            if found:
                field=found[1].lower();skip=field in options
                if skip:body.append(field+': '+options[field].replace('\n','\n  ')+'\n');remaining.discard(field)
            elif line and not line[:1].isspace():skip=False
            if skip and (found or line[:1].isspace()):continue
            body.append(line)
        body.extend(k+': '+options[k].replace('\n','\n  ')+'\n' for k in sorted(remaining));out.append(''.join(body))
    return ''.join(out)+render({s:v for s,v in records.items() if s not in seen})


def footer_text(records, source=KLIPPER_SOURCE):
    """Serialize the pinned native data format without loading application code.

    Header and stdlib ConfigParser.write match pinned ConfigFileReader; native
    writer/parser tests establish recognition. This does not invent measurements.
    """
    if not records:return ''
    import io
    header='\n#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# DO NOT EDIT THIS BLOCK OR BELOW. The contents are auto-generated.\n#*#\n'
    parser=configparser.RawConfigParser(interpolation=None);parser.read_dict(records)
    stream=io.StringIO();parser.write(stream)
    return '\n'+header.rstrip()+'\n'+'\n'.join(('#*# '+line).strip() for line in stream.getvalue().split('\n'))+'\n'


def canonical(config):
    return {s:{k.lower():' '.join(str(v).split()) for k,v in options.items()} for s,options in config.items() if not s.startswith('include ')}


def calibration_group(section):
    if section in ('heater_bed','extruder') or section.startswith('heater_generic '):return section
    return 'motion' if section=='input_shaper' else 'geometry'


def calibration_sources(draft,catalog):
    """Active source/component identity per measurement dependency group."""
    from sv08_printer_compose import validate_plan
    closure=validate_plan(draft['definition_plan'],catalog)[0] if 'definition_plan' in draft else {}
    groups={'geometry':{'bed','extruder','probe','motor','sensor'},'motion':{'extruder','motor','accelerometer'}}
    for device in draft['devices']:
        if device['kind'] in ('bed','extruder','chamber'):
            section=device['name'] if device['kind']!='chamber' else 'heater_generic '+device['name']
            groups[section]={device['kind'],'sensor'}
    result={}
    for group,kinds in groups.items():
        selected=[copy.deepcopy(d) for d in draft['devices'] if d['kind'] in kinds]
        if group not in ('geometry','motion'):
            heater=next((d for d in selected if d['name']==group or 'heater_generic '+d['name']==group),None)
            selected=[d for d in selected if heater and d['name'] in (heater['name'],heater['settings'].get('sensor'))]
        names={d['name'] for d in selected};roles={d['board'] for d in selected}
        for device in selected:
            for field in ('z_offset','pid_kp','pid_ki','pid_kd','position_endstop','control'):device['settings'].pop(field,None)
        sources={ident:digest(record) for ident,record in closure.items() if any(c['name'] in names for c in record.get('components',[]))}
        boards={r:draft['boards'][r] for r in roles}
        assets=draft.get('definition_plan',{}).get('runtime_assets',{})
        mappings=[{k:v for k,v in b.items() if k!='presets'} for b in assets.get('boards',[]) if b['role'] in roles]
        settings=[{k:v for k,v in d['printer_settings'].items() if k!='geometry'} for d in closure.values() if d.get('printer_settings')] if group in ('geometry','motion') else []
        edits={target:value for target,value in draft.get('calibration_edits',{}).items() if target.split('.',1)[0] in names and (group not in ('geometry','motion') or target.split('.',1)[1] in ('z_offset','position_endstop'))}
        result[group]=digest(dict(devices=selected,sources=sources,boards=boards,mappings=mappings,settings=settings,edits=edits))
    return result


if __name__=='__main__':main()
