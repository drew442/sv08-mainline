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
import math
from pathlib import Path
import re

from sv08_printer_catalog import BUNDLE_LIMIT, digest, strict_json

KLIPPER_REVISION = 'f0892d82b0f1c1228454f09eb508eddde2250f4b'
CONFIGFILE_SHA256 = 'c4049b906b5341ad492105901515c6d9a4504d980098f9ce346df48388c53cf4'
KLIPPER_SOURCE = Path('/opt/sv08-mainline/klipper')
PROFILE_NAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}\Z')
MESH_FIELDS = {'version','points','min_x','max_x','min_y','max_y','x_count','y_count','mesh_x_pps','mesh_y_pps','algo','tension'}
SHAPER_FIELDS = {'shaper_type','shaper_type_x','shaper_type_y','shaper_freq_x','shaper_freq_y','damping_ratio_x','damping_ratio_y'}


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
        if section.startswith('bed_mesh '):
            if set(options)!=MESH_FIELDS or options['version']!='1':raise ValueError('Incomplete or unsupported mesh profile')
            rows=[[float(v) for v in row.split(',')] for row in options['points'].strip().splitlines()]
            if len(rows)!=int(options['y_count']) or any(len(row)!=int(options['x_count']) for row in rows):raise ValueError('Mesh profile dimensions disagree')
            if not float(options['min_x'])<float(options['max_x']) or not float(options['min_y'])<float(options['max_y']):raise ValueError('Mesh profile bounds disagree')
    return records


def split_lane(text):
    """Keep exact non-calibration lines immutable; move known options to root."""
    config=parse(text);known=registry(config);immutable=[];lane={};section=None;moving=False
    for line in text.splitlines(keepends=True):
        stripped=line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            section=stripped[1:-1];moving=False
        match=re.match(r'^([A-Za-z0-9_]+)\s*[:=]',line)
        if match:
            field=match[1].lower();moving=field in known.get(section,set())
            if moving:lane.setdefault(section,{})[field]=config[section][field]
        if moving and (match or line[:1].isspace()):continue
        immutable.append(line)
    return ''.join(immutable),render(lane)


def render(records):
    return ''.join('\n['+s+']\n'+''.join(k+': '+v.replace('\n','\n  ')+'\n' for k,v in sorted(options.items())) for s,options in sorted(records.items()))


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
    """Active structural state, excluding mutable measurements and source history."""
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
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')


if __name__=='__main__':main()
