"""Finite SV08 software adapter. No device access, startup scripts or calibration guesses."""
from io import BytesIO
import hashlib
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

DATA_PATH = '/run/sv08/printer_data'
GCODE_PATH = DATA_PATH + '/gcodes'
MOONRAKER = '''[server]
host: 127.0.0.1
port: 7125
klippy_uds_address: /run/sv08/printer_data/comms/klippy.sock

[machine]
provider: none
validate_service: False
validate_config: False

# No update_manager: applications and the OS are coordinated image payloads.
# Authorization remains enabled; do not trust all LAN clients implicitly.
[authorization]
trusted_clients:
  127.0.0.1

[file_manager]
enable_object_processing: True
'''


NGINX = """# Include from the SV08 host nginx http context; no service activation.
server {
    listen 8080;
    server_name _;
    return 301 https://$host:8443$request_uri;
}
server {
    listen 8443 ssl;
    server_name _;
    ssl_certificate /data/sv08/system/identity/current/services/server.crt;
    ssl_certificate_key /data/sv08/system/identity/current/services/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /usr/share/sv08-mainline/mainsail;
    client_max_body_size 64m;
    location / { try_files $uri $uri/ /index.html; }
    location = /config.json { alias /run/sv08/printer_data/config/mainsail.json; }
    location ~ ^/(printer|server|access|machine|api)/ {
        proxy_pass http://127.0.0.1:7125;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /websocket {
        proxy_pass http://127.0.0.1:7125;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 3600s;
    }
}
"""
MAINSail = dict(defaultLocale='en',defaultMode='dark',hostname=None,port=None,path=None,instancesDB='moonraker',instances=[])


def macro(name, body, rename=None):
    return '\n[gcode_macro '+name+']\n'+('rename_existing: '+rename+'\n' if rename else '')+'gcode:\n'+''.join('  '+line+'\n' for line in body.splitlines())


def support(draft, printer_settings, mode, policies, calibration_pending=False):
    """Project-owned commands parameterised by resolved component settings."""
    setup = mode == 'setup' or calibration_pending
    fans=sorted(d['name'] for d in draft['devices'] if d['kind']=='fan' and d['settings'].get('print_fan', d['name'] in ('part_cooling_front','part_cooling_rear')) is True)
    text='''# SV08 Mainline print interface. Generated from selected hardware.
[virtual_sdcard]
path: /run/sv08/printer_data/gcodes
on_error_gcode:
  TURN_OFF_HEATERS

[display_status]
[respond]
[exclude_object]
'''
    # pause_resume may already be contributed by the hardware input adapter.
    if not any(d['kind']=='input' and d['settings'].get('pause_on_runout') for d in draft['devices']):text+='\n[pause_resume]\n'
    guard='{ action_raise_error("Probe calibration pending: record the measured offset and regenerate Full SV08 before printing") }'
    fan_body='{% set speed = params.S|default(255)|float %}\n{% if speed != speed or speed < 0 or speed > 255 %}\n  { action_raise_error("Fan speed must be between 0 and 255") }\n{% endif %}\n'
    if fans:
        fan_body+='\n'.join('SET_FAN_SPEED FAN='+fan+' SPEED={speed / 255.0}' for fan in fans)
    else:fan_body+='{% if speed > 0 %}\n  { action_raise_error("Select a part cooling fan in Printer hardware") }\n{% endif %}'
    text+=macro('M106',fan_body)+macro('M107','M106 S0')
    text+=macro('PAUSE','PAUSE_BASE', 'PAUSE_BASE')
    text+=macro('RESUME',guard if setup else 'RESUME_BASE {rawparams}', 'RESUME_BASE')
    text+=macro('CANCEL_PRINT','TURN_OFF_HEATERS\nM107\nCANCEL_PRINT_BASE', 'CANCEL_PRINT_BASE')
    text+=macro('PRINT_END','TURN_OFF_HEATERS\nM107\nM400\nM84')
    text+=macro('END_PRINT','PRINT_END')
    if setup:
        text+=macro('PRINT_START',guard)
        text+=macro('SDCARD_PRINT_FILE',guard,'SV08_SDCARD_PRINT_FILE_BASE')
        text+=macro('M24',guard,'M24.1')
    else:
        sensors={d['name']:d for d in draft['devices'] if d['kind']=='sensor'}
        heaters={d['name']:d for d in draft['devices'] if d['kind'] in ('bed','extruder')}
        bed=sensors[heaters['heater_bed']['settings']['sensor']]['settings']
        nozzle=sensors[heaters['extruder']['settings']['sensor']]['settings']
        minimum=heaters['extruder']['settings']['min_extrude_temp']
        start='''{% if 'BED_TEMP' not in params or 'EXTRUDER_TEMP' not in params %}
  { action_raise_error("PRINT_START requires BED_TEMP and EXTRUDER_TEMP from the slicer") }
{% endif %}
{% set bed = params.BED_TEMP|float %}
{% set nozzle = params.EXTRUDER_TEMP|float %}
'''
        start+='{% if bed != bed or nozzle != nozzle or bed < 0 or bed >= '+str(bed['max_temp'])+' or nozzle < '+str(minimum)+' or nozzle >= '+str(nozzle['max_temp'])+' %}\n  { action_raise_error("Requested temperatures exceed selected hardware limits") }\n{% endif %}\n'
        start+='CLEAR_PAUSE\nBED_MESH_CLEAR\nM190 S{bed}\n'
        if policies:start+='SV08_LEVELLING_PRECONDITIONS\n'
        start+='G28\n'
        if 'quad_gantry_level' in printer_settings:start+='QUAD_GANTRY_LEVEL\nG28 Z\n'
        if 'bed_mesh' in printer_settings:start+='BED_MESH_CALIBRATE\n'
        start+='G90\nM109 S{nozzle}'
        # Avoid undefined bed mesh commands for explicitly selected custom bases.
        if 'bed_mesh' not in printer_settings:start=start.replace('BED_MESH_CLEAR\n','')
        text+=macro('PRINT_START',start)
    text+=macro('START_PRINT','PRINT_START {rawparams}')
    text+=macro('SV08_SETUP_STATUS', '{ action_respond_info("'+('Setup only; probe calibration pending; printing blocked' if setup else 'Full configuration; verify installed hardware and commission before printing')+'") }')
    return text


def files(hardware, integration, draft, mode, generator, catalog, calibration_pending=False):
    """Exported files have a closed relative include graph and matching socket paths."""
    result={'printer.cfg':'# Generated by SV08 Mainline. No external factory files required.\n[include hardware.cfg]\n[include mainsail.cfg]\n',
            'hardware.cfg':hardware, 'mainsail.cfg':integration, 'moonraker.conf':MOONRAKER,
            'mainsail.json':json.dumps(MAINSail,indent=2)+'\n','nginx-mainsail.conf':NGINX}
    manifest={'format_version':1,'generator':generator,'catalog':catalog,'mode':mode,
              'printing_enabled':mode=='full' and not calibration_pending,'probe_calibration_pending':calibration_pending,'physical_commissioning':'required separately',
              'draft_sha256':hashlib.sha256(json.dumps(draft,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'files':{n:hashlib.sha256(raw.encode()).hexdigest() for n,raw in sorted(result.items())}}
    result['configuration-manifest.json']=json.dumps(manifest,indent=2,sort_keys=True)+'\n'
    result['README.txt']='''SV08 Mainline generated printer configuration

Private instance bundle: MCU identities are included. Do not publish this ZIP.
Use on the SV08 Mainline host with its installed pinned applications and firmware.
Configuration root: /run/sv08/printer_data/config
G-code files: /run/sv08/printer_data/gcodes
Klipper socket: /run/sv08/printer_data/comms/klippy.sock
Moonraker: loopback port7125. nginx-mainsail.conf redirects port8080 to CA-signed HTTPS on port8443.
The sv08-identity.service provisions persistent authority before web services.
Place mainsail.json in the configuration root. The host web configuration includes
nginx-mainsail.conf from its http context. It preserves Moonraker authentication;
no LAN-wide trusted clients are added. Services remain separately managed by the OS.
Do not install software or start services from this archive.

PRINT_START BED_TEMP=<slicer bed temperature> EXTRUDER_TEMP=<slicer nozzle temperature>
PRINT_END
START_PRINT and END_PRINT are aliases. Purging is the slicer's responsibility.
M106/M107 control the explicitly selected part cooling fans only.
Pending probe calibration blocks file printing, print start and resume.
The sourced factory starting offset is not a measured calibration.
Record measured probe Z offset in Printer hardware; PID calibration can follow.
Application never authorizes heating/motion or claims physical printing readiness.
'''
    return result


def archive(contents):
    output=BytesIO()
    with ZipFile(output,'w',compression=ZIP_DEFLATED,compresslevel=9) as target:
        for name,raw in sorted(contents.items()):
            if '/' in name or name.startswith('.') or '\\' in name:raise ValueError('Unsafe exported configuration name')
            entry=ZipInfo('sv08-printer-configuration/'+name,date_time=(2020,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100600<<16;entry.compress_type=ZIP_DEFLATED
            target.writestr(entry,raw.encode(),compresslevel=9)
    return output.getvalue()
