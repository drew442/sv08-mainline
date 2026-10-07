"""Finite supported factory/mainline fields; shared creator and runtime vocabulary."""
FIELDS = {'sensor': {'pin': 'adc',
            'curve': 'curve',
            'pullup_resistor': 'positive',
            'min_temp': 'number',
            'max_temp': 'number',
            'custom_curve': 'thermistor_points'},
 'input': {'pin': 'input',
           'invert': 'boolean',
           'digital_pullup': 'boolean',
           'pause_on_runout': 'boolean',
           'event_delay': 'nonnegative',
           'pause_delay': 'nonnegative'},
 'probe': {'pin': 'probe',
           'invert': 'boolean',
           'digital_pullup': 'boolean',
           'x_offset': 'number',
           'y_offset': 'number',
           'z_offset': 'number',
           'z_offset_start': 'number',
           'speed': 'positive',
           'samples': 'integer',
           'sample_retract_dist': 'positive',
           'lift_speed': 'positive',
           'samples_result': 'samples_result',
           'samples_tolerance': 'positive',
           'samples_tolerance_retries': 'nonnegative_integer'},
 'fan': {'print_fan': 'boolean', 'pin': 'fan', 'invert': 'boolean', 'max_power': 'fraction'},
 'bed': {'pin': 'heater',
         'invert': 'boolean',
         'sensor': 'name',
         'max_power': 'fraction',
         'control': 'control',
         'pid_kp': 'positive',
         'pid_ki': 'positive',
         'pid_kd': 'positive',
         'verify_max_error': 'positive',
         'verify_check_gain_time': 'positive',
         'verify_hysteresis': 'positive',
         'verify_heating_gain': 'positive'},
 'motor': {'connector': 'motor',
           'invert_dir': 'boolean',
           'invert_enable': 'boolean',
           'microsteps': 'integer',
           'rotation_distance': 'positive',
           'run_current': 'positive',
           'current_rating_rms': 'positive',
           'sense_resistor': 'positive',
           'uart_address': 'address',
           'position_min': 'number',
           'position_max': 'number',
           'position_endstop': 'number',
           'homing_speed': 'positive',
           'endstop_pin': 'input',
           'endstop_invert': 'boolean',
           'endstop_pullup': 'boolean',
           'gear_ratio': 'ratio',
           'full_steps_per_rotation': 'integer',
           'interpolate': 'boolean',
           'stealthchop_threshold': 'nonnegative',
           'endstop_mode': 'endstop_mode',
           'driver_sgthrs': 'byte',
           'homing_retract_dist': 'nonnegative',
           'homing_positive_dir': 'boolean',
           'homing_retract_speed': 'positive',
           'second_homing_speed': 'positive'},
 'extruder': {'connector': 'motor',
              'invert_dir': 'boolean',
              'invert_enable': 'boolean',
              'microsteps': 'integer',
              'rotation_distance': 'positive',
              'run_current': 'positive',
              'current_rating_rms': 'positive',
              'sense_resistor': 'positive',
              'uart_address': 'address',
              'pin': 'heater',
              'invert': 'boolean',
              'sensor': 'name',
              'max_power': 'fraction',
              'control': 'control',
              'pid_kp': 'positive',
              'pid_ki': 'positive',
              'pid_kd': 'positive',
              'nozzle_diameter': 'positive',
              'filament_diameter': 'positive',
              'min_extrude_temp': 'number',
              'gear_ratio': 'ratio',
              'full_steps_per_rotation': 'integer',
              'interpolate': 'boolean',
              'stealthchop_threshold': 'nonnegative',
              'verify_max_error': 'positive',
              'verify_check_gain_time': 'positive',
              'verify_hysteresis': 'positive',
              'verify_heating_gain': 'positive'},
 'chamber': {'pin': 'heater',
             'invert': 'boolean',
             'sensor': 'name',
             'max_power': 'fraction',
             'control': 'control',
             'max_delta': 'positive'},
 'heater_fan': {'pin': 'fan',
                'invert': 'boolean',
                'max_power': 'fraction',
                'kick_start_time': 'nonnegative',
                'heater': 'name',
                'heater_temp': 'positive',
                'tachometer_pin': 'input',
                'tachometer_ppr': 'positive',
                'tachometer_poll_interval': 'positive'},
 'output': {'pin': 'output',
            'invert': 'boolean',
            'pwm': 'boolean',
            'value': 'unit_interval',
            'shutdown_value': 'unit_interval',
            'cycle_time': 'positive'},
 'neopixel': {'pin': 'output',
              'chain_count': 'integer',
              'color_order': 'color_order',
              'initial_red': 'unit_interval',
              'initial_green': 'unit_interval',
              'initial_blue': 'unit_interval'},
 'display': {'cs_pin': 'output',
             'a0_pin': 'output',
             'rst_pin': 'output',
             'encoder_a': 'input',
             'encoder_b': 'input',
             'click_pin': 'input',
             'encoder_pullup': 'boolean',
             'click_pullup': 'boolean',
             'click_invert': 'boolean',
             'miso_pin': 'input',
             'mosi_pin': 'output',
             'sclk_pin': 'output',
             'contrast': 'byte'},
 'accelerometer': {'cs_pin': 'output',
                   'miso_pin': 'input',
                   'mosi_pin': 'output',
                   'sclk_pin': 'output',
                   'spi_speed': 'positive'},
 'mcu_temperature': {'min_temp': 'number', 'max_temp': 'number'},
 'pressure_switch': {'pin': 'input', 'invert': 'boolean', 'digital_pullup': 'boolean'}}
LEGACY_FIELDS = {'sensor': ['pin', 'curve', 'pullup_resistor', 'min_temp', 'max_temp', 'custom_curve'],
 'input': ['pin', 'invert', 'digital_pullup'],
 'probe': ['pin', 'invert', 'digital_pullup', 'x_offset', 'y_offset', 'z_offset'],
 'fan': ['pin', 'invert', 'max_power'],
 'bed': ['pin', 'invert', 'sensor', 'max_power', 'control', 'pid_kp', 'pid_ki', 'pid_kd'],
 'motor': ['connector',
           'invert_dir',
           'invert_enable',
           'microsteps',
           'rotation_distance',
           'run_current',
           'current_rating_rms',
           'sense_resistor',
           'uart_address',
           'position_min',
           'position_max',
           'position_endstop',
           'homing_speed',
           'endstop_pin',
           'endstop_invert',
           'endstop_pullup',
           'gear_ratio'],
 'extruder': ['connector',
              'invert_dir',
              'invert_enable',
              'microsteps',
              'rotation_distance',
              'run_current',
              'current_rating_rms',
              'sense_resistor',
              'uart_address',
              'pin',
              'invert',
              'sensor',
              'max_power',
              'control',
              'pid_kp',
              'pid_ki',
              'pid_kd',
              'nozzle_diameter',
              'filament_diameter',
              'min_extrude_temp',
              'gear_ratio'],
 'chamber': ['pin', 'invert', 'sensor', 'max_power', 'control', 'max_delta']}
ELECTRICAL = ("adc", "heater", "fan", "probe", "input", "output", "motor")
CHOICES = {"endstop_mode": ("physical", "sensorless"), "samples_result": ("average", "median"), "color_order": ("RGB", "GRB", "BRG", "BGR", "RBG", "GBR")}


def compatible_mapping(a,b):
    """Additional documented pins do not alter existing electrical identities."""
    ignored={'presets','signals','connectors','channel_counts'}
    if {k:v for k,v in a.items() if k not in ignored}!={k:v for k,v in b.items() if k not in ignored}:return False
    def electrical(value):return {k:v for k,v in value.items() if k not in ('source','evidence')}
    return all(electrical(a[field][key])==electrical(b[field][key]) for field in ('signals','connectors') for key in a[field].keys() & b[field].keys())


def validate_printer_settings(settings,catalog):
    from sv08_printer_catalog import keys,GEOMETRY
    keys(settings,('geometry','bed_mesh','quad_gantry_level','safe_z_home'))
    for group,values in settings.items():
        if group=='geometry':
            keys(values,(*GEOMETRY,'square_corner_velocity'),GEOMETRY)
            for value in values.values():catalog.number(value,'positive')
            continue
        shapes={'bed_mesh':{'speed','horizontal_move_z','mesh_min','mesh_max','probe_count','algorithm','bicubic_tension','split_delta_z','mesh_pps','adaptive_margin','fade_start','fade_end','fade_target'},'quad_gantry_level':{'gantry_corners','points','speed','horizontal_move_z','retry_tolerance','retries','max_adjust'},'safe_z_home':{'home_xy_position','speed','z_hop','z_hop_speed'}}
        keys(values,shapes[group])
        for key,value in values.items():
            if key=='algorithm':
                if value not in ('bicubic','lagrange'):raise ValueError('Unsupported mesh algorithm')
            elif key in ('gantry_corners','points'):
                if not isinstance(value,list) or len(value)!=(2 if key=='gantry_corners' else 4):raise ValueError('Invalid gantry coordinates')
                for point in value:_pair(point,catalog)
            elif key in ('mesh_min','mesh_max','home_xy_position','probe_count','mesh_pps'):
                _pair(value,catalog,'integer' if key in ('probe_count','mesh_pps') else 'number')
            else:catalog.number(value,'nonnegative_integer' if key=='retries' else 'nonnegative')
        if group=='bed_mesh' and 'mesh_min' in values and 'mesh_max' in values:
            if any(a>=b for a,b in zip(values['mesh_min'],values['mesh_max'])):raise ValueError('Invalid mesh bounds')
        for key in ('speed','horizontal_move_z','retry_tolerance','max_adjust','z_hop_speed'):
            if key in values and values[key]<=0:raise ValueError('Positive motion setting required')
    return settings


def _pair(value,catalog,typ='number'):
    if not isinstance(value,list) or len(value)!=2:raise ValueError('Coordinate pair required')
    for number in value:catalog.number(number,typ)


def compact_mapping(board):
    """Retain board provenance and exact per-pin lines without repeated citations."""
    import copy
    result=copy.deepcopy(board);result['presets']=[]
    for group in ('signals','connectors'):
        for value in result[group].values():
            source=value['source'];value['source']={k:v for k,v in source.items() if k in ('line','path','revision') and (k=='line' or v!=result['source'].get(k))}
            value.pop('evidence',None) # Board warning/provenance applies to every binding.
    return result
