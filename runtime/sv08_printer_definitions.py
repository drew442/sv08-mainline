"""Draft public data contract, shared by creator tooling and appliance runtime.

No schema fetch, code evaluation, implicit subscription or executable extensions.
"""
import copy
import re
from sv08_printer_catalog import strict_json, encoded, digest, keys, NAME

FORMAT = '0.1'
FILE_LIMIT = 128 * 1024
SOURCE_LIMIT = 384 * 1024
MAX_DEFINITIONS = 32
MAX_DEPTH = 12
CATEGORIES = ('bed','probe','toolhead','filament','boards','cooling','motion')
CAPABILITIES = {'klipper.settings.v1', 'klipper.watermark.v1', 'levelling.condition.v1'}
COMMON = ('format_version','id','version','kind','name','description','aliases','category','hardware','compatibility','sources','license','extensions','dependencies','conflicts','inputs','calibration','unresolved')
KINDS = {'component':('components','connections'), 'assembly':('components','connections','behaviours'), 'board':('mapping',), 'behaviour':('behaviours',)}

def bounded(value, depth=0):
    if depth > 24:raise ValueError('JSON nesting exceeds 24 levels')
    if isinstance(value,dict):
        if len(value)>256:raise ValueError('Object exceeds 256 fields')
        for k,v in value.items():
            if not isinstance(k,str) or len(k)>240:raise ValueError('Invalid field name')
            bounded(v,depth+1)
    elif isinstance(value,list):
        if len(value)>256:raise ValueError('Array exceeds 256 entries')
        for v in value:bounded(v,depth+1)
    elif isinstance(value,str) and len(value)>8192:raise ValueError('Text exceeds limit')

def public_json(raw,limit=FILE_LIMIT):
    value=strict_json(raw,limit);bounded(value);return value

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,79}',value):raise ValueError('Invalid definition ID')

def reference(value):
    keys(value,('source','id','version','sha256'),('id','version','sha256'))
    identifier(value['id'])
    if not re.fullmatch(r'[0-9a-f]{64}',value['sha256']):raise ValueError('Dependency requires SHA256')
    if value.get('source')=='builtin':return
    if 'source' in value and not isinstance(value['source'],str):raise ValueError('Invalid dependency source')

def validate_definition(d,catalog):
    bounded(d)
    if not isinstance(d,dict) or d.get('kind') not in KINDS:raise ValueError('Unsupported record kind')
    keys(d,COMMON+KINDS[d['kind']],('format_version','id','version','kind','name','category','hardware','compatibility','sources','license'))
    for field in ('hardware','extensions','inputs'):
        if field in d and not isinstance(d[field],dict):raise ValueError(field+': object required')
    for field in ('aliases','calibration','unresolved'):
        if field in d and (not isinstance(d[field],list) or not all(isinstance(v,str) for v in d[field])):raise ValueError(field+': string array required')
    for field in ('description','license'):
        if field in d and not isinstance(d[field],str):raise ValueError(field+': string required')
    if d['format_version']!=FORMAT:raise ValueError('Unsupported public format')
    identifier(d['id'])
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?',d['version']):raise ValueError('Version must be immutable semantic version')
    if not isinstance(d['name'],str) or not d['name'].strip():raise ValueError('Definition name required')
    if d['category'] not in CATEGORIES:raise ValueError('Unknown component category')
    keys(d['compatibility'],('requires_capabilities','boards','printers','tested','unknown'),('requires_capabilities',))
    for field in ('requires_capabilities','boards','printers'):
        if field in d['compatibility'] and (not isinstance(d['compatibility'][field],list) or not all(isinstance(v,str) for v in d['compatibility'][field])):raise ValueError('compatibility.'+field+': string array required')
    printers=d['compatibility'].get('printers',[])
    if printers and not set(printers)&{'sv08','sovol-sv08','sv08-mainline'}:raise ValueError('Unsupported printer scope; original SV08 runtime required')
    unsupported=set(d['compatibility']['requires_capabilities'])-CAPABILITIES
    if unsupported:raise ValueError('Unsupported capability: '+', '.join(sorted(unsupported)))
    if not isinstance(d['sources'],list) or not d['sources']:raise ValueError('Operational provenance required')
    for source in d['sources']:
        keys(source,('id','url','revision','sha256','locator','evidence'),('id','locator'))
        if not source.get('url') and not source.get('revision'):raise ValueError('Source URL or revision required')
        for field in ('id','url','revision','sha256','locator'):
            if field in source and not isinstance(source[field],str):raise ValueError('sources.'+field+': string required')
        if source.get('url') and not source['url'].startswith('https://'):raise ValueError('Source URL must use HTTPS')
    for k in d.get('extensions',{}):
        if not re.fullmatch(r'[a-z0-9]+[.:][a-z0-9_.-]+',k):raise ValueError('Metadata extensions must be namespaced')
    for dep in d.get('dependencies',[]):reference(dep)
    for dep in d.get('conflicts',[]):reference(dep)
    for key,inp in d.get('inputs',{}).items():
        identifier(key);keys(inp,('type','label','required','default','choices','target','units','minimum','maximum'),('type','label','target'))
        if inp['type'] not in ('number','boolean','choice','curve','identity'):raise ValueError('Unsupported input type')
        if inp['type']=='choice' and (not inp.get('choices') or not all(isinstance(v,str) for v in inp['choices'])):raise ValueError('Choices must be nonempty strings')
        if 'default' in inp and inp['type']=='identity':raise ValueError('Published controller identity forbidden')
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,39}\.[a-z][a-z0-9_]{0,39}',inp['target']):raise ValueError('Input target must be a semantic field')
        field=inp['target'].split('.')[1]
        allowed={k for fields in catalog.kinds.values() for k,t in fields.items() if t not in ('adc','heater','fan','probe','input','motor','thermistor_points')}|{'identity'}
        if field not in allowed:raise ValueError('Unsupported input target field')
        for bound in ('minimum','maximum'):
            if bound in inp:catalog.number(inp[bound],'number')
        if inp.get('minimum',float('-inf'))>inp.get('maximum',float('inf')):raise ValueError('Contradictory input bounds')
        if 'default' in inp:
            value=inp['default']
            if inp['type']=='number':
                catalog.number(value,'number')
                if value<inp.get('minimum',float('-inf')) or value>inp.get('maximum',float('inf')):raise ValueError('Input default outside bounds')
            elif inp['type']=='boolean' and type(value) is not bool:raise ValueError('Boolean input default required')
            elif inp['type']=='curve' and value not in catalog.curves:raise ValueError('Unsupported default curve')
            elif inp['type']=='choice' and value not in inp.get('choices',[]):raise ValueError('Default must be a declared choice')
    names=set()
    for component in d.get('components',[]):
        keys(component,('name','kind','board','settings','endpoints'),('name','kind','board','settings','endpoints'))
        name=component['name']
        if not isinstance(name,str) or not NAME.fullmatch(name) or name in names:raise ValueError('Duplicate/invalid semantic device role')
        names.add(name)
        if component['kind'] not in catalog.kinds or component['board'] not in ('main','tool','chamber'):raise ValueError('Unsupported component kind/board role')
        keys(component['settings'],catalog.kinds[component['kind']])
        for field,value in component['settings'].items():
            typ=catalog.kinds[component['kind']][field]
            if typ=='curve' and value not in catalog.curves:raise ValueError('Unsupported sensor curve')
            if typ=='boolean' and type(value) is not bool:raise ValueError('Boolean setting required')
            if typ in ('positive','number','fraction','integer','address'):catalog.number(value,typ)
            if typ=='name' and (not isinstance(value,str) or not NAME.fullmatch(value)):raise ValueError('Invalid sensor role')
            if typ=='control' and value not in ('watermark','pid'):raise ValueError('Unsupported heater control')
            if field=='run_current' and value>2:raise ValueError('Driver software current limit exceeded')
        for field in component['settings']:
            if catalog.kinds[component['kind']][field] in ('adc','heater','fan','probe','input','motor'):raise ValueError('Portable settings require endpoint bindings, not GPIO')
            if field in ('custom_curve','pid_kp','pid_ki','pid_kd','current_rating_rms','z_offset'):raise ValueError('Instance calibration/rating cannot be a universal default')
        for field,endpoint in component['endpoints'].items():
            if field not in catalog.kinds[component['kind']]:raise ValueError('Unknown endpoint field')
            if catalog.kinds[component['kind']][field] not in ('adc','heater','fan','probe','input','motor'):raise ValueError('Endpoint must bind a connection field')
            if not isinstance(endpoint,str):raise ValueError('Invalid endpoint binding')
    for inp in d.get('inputs',{}).values():
        name,field=inp['target'].split('.',1)
        if field=='identity':
            if inp['type']!='identity' or name not in ('main','tool','chamber'):raise ValueError('Identity input must address a controller role')
            continue
        component=next((c for c in d.get('components',[]) if c['name']==name),None)
        if component:
            typ=catalog.kinds[component['kind']].get(field)
            compatible={'number':('positive','number','fraction','integer','address'),'boolean':('boolean',),'curve':('curve',),'choice':('control','ratio','name')}
            if typ not in compatible.get(inp['type'],()):raise ValueError('Input type/target field mismatch')
    endpoints=set()
    for conn in d.get('connections',[]):
        keys(conn,('endpoint','board','connector','capability','board_ids','contact'),('endpoint','board','connector','capability','board_ids'))
        if conn['endpoint'] in endpoints:raise ValueError('Duplicate connection endpoint')
        endpoints.add(conn['endpoint'])
        if conn['board'] not in ('main','tool','chamber'):raise ValueError('Unsupported board role')
        if conn['capability'] not in ('adc','heater','fan','probe','input','motor'):raise ValueError('Unsupported connection capability')
        if not isinstance(conn['board_ids'],list) or not conn['board_ids']:raise ValueError('Exact board scope required')
        for board_id in conn['board_ids']:
            if board_id not in catalog.boards:continue # May be supplied by a pinned board dependency.
            board=catalog.boards[board_id]
            mapping=board['motors'] if conn['capability']=='motor' else board['connectors']
            if conn['connector'] not in mapping:raise ValueError('Connector not documented for board')
            if conn['capability']!='motor' and mapping[conn['connector']]['capability']!=conn['capability']:raise ValueError('Connector capability mismatch')
    for component in d.get('components',[]):
        if not set(component['endpoints'].values())<=endpoints:raise ValueError('Missing connection endpoint')
        bindings={c['endpoint']:c for c in d.get('connections',[])}
        for field,endpoint in component['endpoints'].items():
            if bindings[endpoint]['capability']!=catalog.kinds[component['kind']][field]:raise ValueError('Endpoint capability mismatch')
    if d['kind']=='board':
        # Reuse the exact same finite circuit/mapping validator as built-ins.
        keys(d['mapping'],('channel_counts','channel_scope','connectors','evidence','id','label','motors','presets','reservation_evidence','reserved_pins','reserved_scope','revision','role','sharing_rules','signals','source','supported_transports','unknowns','warning'))
        for field in ('signals','connectors','motors'):
            if not isinstance(d['mapping'].get(field),dict):raise ValueError('mapping.'+field+': object required')
        for signal in d['mapping']['signals'].values():keys(signal,('capabilities','evidence','reserved','source'))
        for connector in d['mapping']['connectors'].values():keys(connector,('capability','contact','evidence','label','pin','source'))
        for motor in d['mapping']['motors'].values():keys(motor,('dir','enable','step','uart'))
        if d['mapping'].get('presets'):raise ValueError('Public board mappings cannot embed component presets')
        data=copy.deepcopy(catalog.data)
        if d['mapping']['id'] in catalog.boards:
            if {k:v for k,v in d['mapping'].items() if k!='presets'} != {k:v for k,v in catalog.boards[d['mapping']['id']].items() if k!='presets'}:raise ValueError('Board identity conflicts with existing mapping')
        else:data['boards'].append(d['mapping'])
        from sv08_printer_catalog import Catalog
        candidate=object.__new__(Catalog);candidate.data=data;candidate.supported=True;candidate.validate_catalog()
    if d['kind']=='component' and not d.get('components') and not d.get('unresolved'):raise ValueError('Component has no contribution or declared gap')
    if d['kind']=='assembly' and not any(d.get(k) for k in ('components','dependencies','behaviours','unresolved')):raise ValueError('Assembly has no contribution or declared gap')
    if d['kind']=='behaviour' and not d.get('behaviours') and not d.get('unresolved'):raise ValueError('Behaviour requires explicit semantics or declared gap')
    for behaviour in d.get('behaviours',[]):validate_behaviour(behaviour)
    return d

def validate_behaviour(b):
    if b.get('operation')=='none':
        keys(b,('hook','operation','sources'),('hook','operation','sources'))
        if b['hook']!='levelling.preconditions' or not b['sources']:raise ValueError('Explicit no-additional-check requires a supported hook and provenance')
        return
    keys(b,('hook','operation','sensor','comparison','threshold','upper','abort','sources'),('hook','operation','sensor','comparison','threshold','abort','sources'))
    if b['hook']!='levelling.preconditions' or b['operation']!='check' or b['comparison'] not in ('at_least','at_most','within_range') or b['abort']!='error':raise ValueError('Unsupported behaviour semantics')
    if not NAME.fullmatch(b['sensor']):raise ValueError('Invalid behaviour sensor')
    if ('upper' in b)!=(b['comparison']=='within_range'):raise ValueError('Upper threshold belongs only to a range condition')
    for n in ['threshold']+(['upper'] if b['comparison']=='within_range' else []):
        if type(b.get(n)) not in (int,float):raise ValueError('Behaviour requires explicit numeric condition')
        import math
        if not math.isfinite(b[n]):raise ValueError('Behaviour requires finite numeric condition')
    if b['comparison']=='within_range' and b['upper']<b['threshold']:raise ValueError('Contradictory temperature range')
    if not b['sources']:raise ValueError('Behaviour provenance required')

def builtins(catalog):
    """Migration adapter emits the SAME public records accepted for creator data."""
    records=[]
    for board in catalog.boards.values():
        if board['id'] not in ('sv08-main','sv08-tool'):continue
        source=board['source']
        records.append(dict(format_version=FORMAT,id=board['id']+'.board',version='0.1.0',kind='board',name=board['label'],description=board['warning'],category='boards',hardware={'product':board['label'],'revision':board['revision']},compatibility={'requires_capabilities':['klipper.settings.v1'],'unknown':board['unknowns']},sources=[dict(id='reference',url=source.get('url','https://github.com/drew442/sv08-mainline'),revision=source['revision'],locator=source['path'])],license='GPL-3.0-or-later',mapping={**copy.deepcopy(board),'presets':[]}))
        for p in board.get('presets',[]):
            if p['id'] in ('funssor_cn3d_bed','bed_sensor','hotend_sensor'):continue
            components=[];connections=[]
            for dev in p['devices']:
                settings={};endpoints={}
                for field,value in dev['settings'].items():
                    typ=catalog.kinds[dev['kind']][field]
                    if typ in ('adc','heater','fan','probe','input','motor'):
                        endpoint=dev['name']+'.'+field;endpoints[field]=endpoint
                        connector=value if typ=='motor' else next((name for name,c in board['connectors'].items() if c['pin']==value and c['capability']==typ),None)
                        if connector is None:raise ValueError('Built-in lacks documented endpoint')
                        connections.append(dict(endpoint=endpoint,board=board['role'],connector=connector,capability=typ,board_ids=[board['id']],contact=None))
                    elif field not in ('pid_kp','pid_ki','pid_kd','current_rating_rms','z_offset'):settings[field]='watermark' if field=='control' and value=='pid' else value
                components.append(dict(name=dev['name'],kind=dev['kind'],board=board['role'],settings=settings,endpoints=endpoints))
            kinds={c['kind'] for c in components}
            category='bed' if 'bed' in kinds else 'toolhead' if 'extruder' in kinds else 'probe' if 'probe' in kinds else 'cooling' if kinds&{'fan','chamber'} else 'motion' if 'motor' in kinds else 'filament' if 'input' in kinds else 'boards'
            source=board['source']
            records.append(dict(format_version=FORMAT,id=board['id']+'.'+p['id'],version='0.1.0',kind='assembly',name=p['label'],description=p.get('notes',''),aliases=['Funnsor'] if 'funssor' in p['id'] else [],category=category,hardware={'product':p['label'],'revision':board['revision']},compatibility={'requires_capabilities':['klipper.settings.v1'],'boards':[board['id']],'unknown':board['unknowns']},sources=[dict(id='reference',url=source.get('url','https://github.com/drew442/sv08-mainline'),revision=source['revision'],locator=source['path'])],license='GPL-3.0-or-later',components=components,connections=connections,calibration=['thermal_pid'] if kinds&{'bed','extruder'} else []))
    for record in records:
        if any(c['kind'] in ('bed','extruder') for c in record.get('components',[])):
            record['description']+=' Uncalibrated heater control uses watermark; measured PID calibration is a separate commissioning task.'
            record['sources'].append(dict(id='commissioning-policy',url='https://github.com/drew442/sv08-mainline/blob/main/runtime/sv08_printer_definitions.py',revision='generator-6',locator='builtins: exclude instance calibration and physical motor ratings; watermark until measured PID gains'))
    return records

def resolve(ref, snapshots, catalog, depth=0, visiting=None, versions=None):
    if depth>MAX_DEPTH:raise ValueError('Dependency depth exceeds 12')
    visiting=set() if visiting is None else visiting;versions={} if versions is None else versions
    key=(ref['source'],ref['id']);ident=ref['source']+'::'+ref['id']+'@'+ref['version']
    if ident in visiting:raise ValueError('Definition dependency cycle')
    if key in versions and versions[key]!=(ref['version'],ref['sha256']):raise ValueError('Conflicting dependency versions')
    versions[key]=(ref['version'],ref['sha256'])
    d=snapshots.get(ident)
    if d is None or digest(d)!=ref['sha256'] or d['id']!=ref['id'] or d['version']!=ref['version']:raise ValueError('Pinned definition unavailable or changed')
    validate_definition(d,catalog);result={ident:d};visiting.add(ident)
    for dep in d.get('dependencies',[]):
        r={**dep,'source':dep.get('source',ref['source'])};result.update(resolve(r,snapshots,catalog,depth+1,visiting,versions))
    visiting.remove(ident)
    for conflict in d.get('conflicts',[]):
        target=conflict.get('source',ref['source'])+'::'+conflict['id']+'@'+conflict['version']
        if target in result:raise ValueError('Conflicting selected definitions')
    return result
