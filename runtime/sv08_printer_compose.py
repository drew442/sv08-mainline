"""Pure definition composition, pinned selections and explicit instance overrides."""
import copy
from sv08_printer_catalog import digest, keys
from sv08_printer_definitions import resolve, validate_definition
from sv08_printer_fields import compatible_mapping,compact_mapping


def catalog_for(draft,catalog,records=()):
    """Overlay documented source mappings and saved mappings without mutable lookup."""
    from sv08_printer_catalog import Catalog
    if not catalog.supported:return catalog
    data=copy.deepcopy(catalog.data);boards={b['id']:b for b in data['boards']}
    plan=draft.get('definition_plan',{})
    candidates=[d['mapping'] for d in records if d.get('kind')=='board']
    for b in candidates:
        if b['id'] in boards:
            # Saved assets deliberately omit unused presets; electrical mapping
            # must still agree when an identity exists in the running catalogue.
            if not compatible_mapping(b,boards[b['id']]):raise ValueError('Board identity conflicts with pinned mapping')
            merged=copy.deepcopy(b);existing=boards[b['id']]
            for group in ('signals','connectors'):merged[group]={**copy.deepcopy(existing[group]),**merged[group]}
            merged['presets']=copy.deepcopy(existing.get('presets',[]))
            merged['channel_counts']={cap:sum(cap in s['capabilities'] for s in merged['signals'].values()) for cap in sorted({c for s in merged['signals'].values() for c in s['capabilities']})}
            boards[b['id']]=merged
        else:boards[b['id']]=copy.deepcopy(b)
    assets=plan.get('runtime_assets',{})
    for b in assets.get('boards',[]):boards[b['id']]=copy.deepcopy(b)
    curves={c['id']:c for c in data['curves']}
    curves.update({c['id']:copy.deepcopy(c) for c in assets.get('curves',[])})
    data['curves']=list(curves.values())
    data['boards']=list(boards.values());candidate=object.__new__(Catalog)
    candidate.data=data;candidate.supported=True;candidate.validate_catalog();candidate.revision=catalog.revision
    return candidate

def connection_devices(definition, draft, catalog):
    connections={x['endpoint']:x for x in definition.get('connections',[])};devices=[]
    for component in definition.get('components',[]):
        c=copy.deepcopy(component);settings=c['settings']
        for field,endpoint in c['endpoints'].items():
            binding=connections[endpoint];role=binding['board'];selection=draft['boards'].get(role,{})
            if selection.get('id') not in binding['board_ids']:raise ValueError(endpoint+': choose a compatible board reference')
            board=catalog.board(draft,role)
            if binding['capability']=='motor':settings[field]=binding['connector']
            else:
                connector=board['connectors'].get(binding['connector'])
                if not connector or connector['capability']!=binding['capability']:raise ValueError(endpoint+': incompatible connector')
                settings[field]=connector['pin']
        devices.append(dict(name=c['name'],kind=c['kind'],board=c['board'],settings=settings))
    return devices


def apply_inputs(draft,catalog):
    result=copy.deepcopy(draft);plan=result.get('definition_plan')
    if not plan:return result
    closure,_=validate_plan(plan,catalog)
    for d in closure.values():
        for inp in d.get('inputs',{}).values():
            target=inp['target'];values=plan.get('instance_values',{})
            if target not in values and 'default' not in inp:continue
            value=values[target] if target in values else inp['default'];name,field=target.split('.',1)
            if field in ('identity','transport','reference_ack') and name in result['boards']:result['boards'][name][field]=value
            else:
                device=next((c for c in result['devices'] if c['name']==name),None)
                if not device:continue # Missing contributions are labelled by generation.
                if field not in catalog.kinds[device['kind']]:raise ValueError('Instance input target is unavailable')
                device['settings'][field]=copy.deepcopy(value)
    return result


def remove_definition(catalog,draft,ref):
    result=copy.deepcopy(draft);plan=result.get('definition_plan')
    if not plan or ref not in plan['selections']:raise ValueError('Definition selection is unavailable')
    before,_=validate_plan(plan,catalog);plan['selections'].remove(ref)
    # Inputs belong to retained definitions, rather than to the subscription.
    retained={}
    for selection in plan['selections']:retained.update(resolve(selection,plan['snapshots'],catalog,replacements=plan.get('replacements',{})))
    targets={i['target'] for d in retained.values() for i in d.get('inputs',{}).values()}
    plan['instance_values']={k:v for k,v in plan.get('instance_values',{}).items() if k in targets}
    owned={(c['board'],c['name']) for d in before.values() for c in d.get('components',[])}
    kept={(c['board'],c['name']) for d in retained.values() for c in d.get('components',[])}
    removed=owned-kept
    for device in result['devices']:
        if (device['board'],device['name']) not in removed and (device['board'],device['settings'].get('sensor')) in removed:raise ValueError('Definition sensor is used by another heater')
    result['devices']=[d for d in result['devices'] if (d['board'],d['name']) not in removed]
    plan['runtime_assets']=runtime_assets(result,catalog);catalog.validate(result)
    return result

def validate_plan(plan, catalog):
    keys(plan,('format_version','selections','snapshots','origins','overrides','runtime_assets','instance_values','replacements'),('format_version','selections','snapshots'))
    if plan['format_version']!=1 or not isinstance(plan['selections'],list) or len(plan['selections'])>32:raise ValueError('Unsupported or oversized definition plan')
    replacements=plan.get('replacements',{})
    if not isinstance(replacements,dict) or len(replacements)>32 or any(k not in plan['snapshots'] for k in replacements):raise ValueError('Invalid dependency replacement map')
    for ref in replacements.values():keys(ref,('source','id','version','sha256','commit'),('source','id','version','sha256','commit'))
    closure={};versions={}
    for ref in plan['selections']:
        keys(ref,('source','id','version','sha256','commit'),('source','id','version','sha256','commit'))
        found=resolve(ref,plan['snapshots'],catalog,versions=versions,replacements=replacements)
        closure.update(found)
    owners={};hooks={}
    for ident,d in sorted(closure.items()):
        for c in d.get('components',[]):
            key=(c['board'],c['name'])
            if key in owners and owners[key]!=ident:raise ValueError('Conflicting component ownership')
            owners[key]=ident
        for b in d.get('behaviours',[]):
            if b['operation']=='none':continue
            hook=b['hook'];checks=hooks.setdefault(hook,[])
            if b not in checks:checks.append(b)
        source=ident.split('::')[0]
        for conflict in d.get('conflicts',[]):
            target=conflict.get('source',source)+'::'+conflict['id']+'@'+conflict['version']
            if target in closure:raise ValueError('Conflicting selected definitions')
    for hook,checks in hooks.items():
        bounds={}
        for b in checks:
            lower,upper=bounds.get(b['sensor'],(float('-inf'),float('inf')))
            if b['comparison'] in ('at_least','within_range'):lower=max(lower,b['threshold'])
            if b['comparison']=='at_most':upper=min(upper,b['threshold'])
            if b['comparison']=='within_range':upper=min(upper,b['upper'])
            if lower>upper:raise ValueError('Conflicting levelling policies')
            bounds[b['sensor']]=(lower,upper)
        hooks[hook]=sorted(checks,key=lambda b:(b['sensor'],b['comparison'],b['threshold'],b.get('upper',0)))
    values=plan.get('instance_values',{})
    if not isinstance(values,dict):raise ValueError('Invalid instance input map')
    inputs={inp['target']:inp for d in closure.values() for inp in d.get('inputs',{}).values()}
    if set(values)-set(inputs):raise ValueError('Unknown instance input')
    for target,value in values.items():
        inp=inputs[target]
        if inp['type']=='number':
            catalog.number(value,'number')
            if value<inp.get('minimum',float('-inf')) or value>inp.get('maximum',float('inf')):raise ValueError('Instance input outside declared bounds')
        elif inp['type']=='identity':
            import re
            if not isinstance(value,str) or not re.fullmatch(r'(?:/dev/[A-Za-z0-9_./:-]{1,200}|[0-9a-f]{12})',value) or '..' in value.split('/'):raise ValueError('Invalid private controller identity')
        elif inp['type']=='boolean' and type(value) is not bool:raise ValueError('Boolean instance input required')
        elif inp['type']=='curve' and value not in catalog.curves:raise ValueError('Unknown instance sensor curve')
        elif inp['type']=='choice' and value not in inp.get('choices',[]):raise ValueError('Unsupported instance choice')
    return closure, hooks


def select_definition(catalog, draft, ref, snapshots):
    result=copy.deepcopy(draft);plan=result.setdefault('definition_plan',dict(format_version=1,selections=[],snapshots={},origins={}))
    old_snapshots=copy.deepcopy(plan['snapshots']);combined={**plan['snapshots'],**snapshots};closure=resolve(ref,combined,catalog)
    ident=ref['source']+'::'+ref['id']+'@'+ref['version'];definition=closure[ident]
    # Board dependencies are admitted before their named component connections.
    boards=[d for d in closure.values() if d['kind']=='board']
    if boards:
        assets=plan.get('runtime_assets',{});incoming_ids={d['mapping']['id'] for d in boards}
        if assets:assets['boards']=[b for b in assets.get('boards',[]) if b['id'] not in incoming_ids]
        catalog=catalog_for(result,catalog,boards)
        for board in boards:
            role=board['mapping']['role'];board_id=board['mapping']['id']
            if result['boards'].get(role,{}).get('id') and result['boards'][role]['id']!=board_id:
                result=remap_board(result,role,board_id,catalog)['draft'];plan=result['definition_plan']
            elif not result['boards'].get(role,{}).get('id'):result['boards'][role]={'id':board_id}
    if definition.get('printer_settings'):
        result['geometry']={**copy.deepcopy(definition['printer_settings'].get('geometry',{})),**result['geometry']}
    old=[r for r in plan['selections'] if r['source']==ref['source'] and r['id']==ref['id']]
    active,_=validate_plan(plan,catalog)
    incoming=[]
    for dependency,d in sorted(closure.items()):
        mapped=connection_devices(d,result,catalog)
        if dependency in active and dependency!=ident:
            actual={(c['board'],c['name']):c for c in draft['devices']}
            mapped=[copy.deepcopy(actual.get((c['board'],c['name']),c)) for c in mapped]
        incoming+=mapped
    names={d['name'] for d in incoming};sensor_inputs={(d['board'],d['settings'].get('pin')) for d in incoming if d['kind']=='sensor'}
    removed=names|{d['name'] for d in result['devices'] if d['kind']=='sensor' and (d['board'],d['settings'].get('pin')) in sensor_inputs}
    if any(d['name'] in names and not any(d['name']==n['name'] and d['board']==n['board'] for n in incoming) for d in result['devices']):raise ValueError('Component name belongs to another board')
    if any(d['name'] not in removed and d['settings'].get('sensor') in removed for d in result['devices']):raise ValueError('Component sensor is used by another heater')
    # For an explicit version update, retain field overrides against the old base.
    if old:
        old_ident=old[0]['source']+'::'+old[0]['id']+'@'+old[0]['version'];prior=old_snapshots[old_ident]
        prior_devices={d['name']:d for d in connection_devices(prior,draft,catalog)}
        actual={d['name']:d for d in draft['devices']}
        for device in incoming:
            base=prior_devices.get(device['name']);current=actual.get(device['name'])
            if not base or not current:continue
            for field,value in current['settings'].items():
                if base['settings'].get(field)!=value and field not in ('pid_kp','pid_ki','pid_kd','custom_curve'):
                    device['settings'][field]=copy.deepcopy(value)
    plan['snapshots'].update(closure)
    incoming_slots={(d['board'],d['name']) for d in incoming}
    def matches(a,b):
        if a['kind']=='board' or b['kind']=='board':return a['kind']==b['kind']=='board' and a['mapping']['role']==b['mapping']['role']
        ac=a.get('components',[]);bc=b.get('components',[])
        return bool({(c['board'],c['name']) for c in ac}&{(c['board'],c['name']) for c in bc}) or any(x['kind']==y['kind'] and x['kind'] in ('bed','extruder','probe','input') and x['board']==y['board'] for x in ac for y in bc)
    def replaces(prior):
        p=plan['snapshots'][prior['source']+'::'+prior['id']+'@'+prior['version']]
        if prior['source']==ref['source'] and prior['id']==ref['id']:return True
        if definition['kind']=='behaviour' or p['kind']=='behaviour':return False
        if definition['kind']=='board':return p['kind']=='board' and p['mapping']['role']==definition['mapping']['role']
        if p['kind']=='board':return p['id'] in {d['id'] for d in boards}
        owned={(c['board'],c['name']) for d in resolve(prior,plan['snapshots'],catalog,replacements=plan.get('replacements',{})).values() for c in d.get('components',[])}
        changed_owners=any(key not in active and {(c['board'],c['name']) for c in d.get('components',[])}&owned for key,d in closure.items())
        return bool(owned) and owned<=incoming_slots and (definition.get('printer_settings') or matches(p,definition) or changed_owners)
    # Explicitly replacing one child customizes an assembly without erasing it.
    replaced=[r for r in plan['selections'] if replaces(r)]
    prior_owners={tuple((r[k] for k in ('source','id','version'))):{(c['board'],c['name']) for d in resolve(r,plan['snapshots'],catalog,replacements=plan.get('replacements',{})).values() for c in d.get('components',[])} for r in plan['selections']}
    substitutions=plan.setdefault('replacements',{})
    if definition.get('printer_settings'):
        for key in closure:substitutions.pop(key,None)
    for key,p in active.items():
        if p['kind'] not in ('assembly','component','board'):continue
        for incoming_key,record in closure.items():
            if key==incoming_key or not matches(p,record):continue
            source=incoming_key.split('::',1)[0]
            substitutions[key]=dict(source=source,id=record['id'],version=record['version'],sha256=digest(record),commit=ref['commit'])
    for key in closure:substitutions.pop(key,None)
    replaced_owners=set();retained_owners=set()
    for prior in plan['selections']:
        owned=prior_owners[tuple(prior[k] for k in ('source','id','version'))]
        (replaced_owners if prior in replaced else retained_owners).update(owned)
    obsolete=replaced_owners-retained_owners-{(d['board'],d['name']) for d in incoming}
    if any((d['board'],d['name']) not in obsolete and (d['board'],d['settings'].get('sensor')) in obsolete for d in result['devices']):raise ValueError('Replaced definition sensor is used by another heater')
    result['devices']=[d for d in result['devices'] if (d['board'],d['name']) not in obsolete]
    result['devices']=[d for d in result['devices'] if d['name'] not in removed]+incoming
    if definition['category']=='bed' and definition['kind']!='behaviour':
        for device in result['devices']:
            if device['kind']=='probe':device['settings'].pop('z_offset',None)
    # Multiple motors, fans and controller roles coexist in their categories.
    plan['selections']=[r for r in plan['selections'] if r not in replaced]+[copy.deepcopy(ref)]
    plan['snapshots'].update(closure)
    plan['origins'].update({d['name']:'user-declared' for d in incoming})
    # Old content remains in saved/restoration envelopes; no mutable lookup is used.
    result=apply_inputs(result,catalog)
    result['definition_plan']['runtime_assets']=runtime_assets(result,catalog)
    catalog.validate(result)
    return result


def migration_preview(draft, catalog, builtin_records):
    """No inferred stock. Exact matching profile data only; unknown stays unknown."""
    result=copy.deepcopy(draft);plan=dict(format_version=1,selections=[],snapshots={},origins={})
    for device in draft['devices']:
        plan['origins'][device['name']]='imported'
    records={d['id']:d for d in builtin_records}
    for role,board in draft['boards'].items():
        for profile in sorted({d.get('profile') for d in draft['devices'] if d['board']==role and d.get('profile')}):
            d=records.get(board.get('id','')+'.'+profile)
            if d:
                ref=dict(source='builtin',id=d['id'],version=d['version'],sha256=digest(d),commit=catalog.revision)
                plan['selections'].append(ref);plan['snapshots']['builtin::'+d['id']+'@'+d['version']]=copy.deepcopy(d)
    result['definition_plan']=plan
    return dict(draft=result,backup=copy.deepcopy(draft),changes=[dict(device=d['name'],origin='imported',status='Definition unassigned' if not d.get('profile') else 'Pinned existing profile') for d in draft['devices']])


def remap_board(draft, role, board_id, catalog):
    result=copy.deepcopy(draft);old=catalog.board(draft,role);new=catalog.boards[board_id]
    if new['role']!=role:raise ValueError('Board role mismatch')
    result['boards'][role]={'id':board_id};rows=[]
    for d in result['devices']:
        if d['board']!=role:continue
        d.pop('profile',None)
        for field in list(d['settings']):
            typ=catalog.kinds[d['kind']][field]
            if typ not in ('adc','heater','fan','probe','input','output','motor'):continue
            value=d['settings'][field];old_connector=next((c for c in old['connectors'].values() if c.get('pin')==value and c['capability']==typ),None)
            matches=[c for c in new['connectors'].values() if old_connector and c['label']==old_connector['label'] and c['capability']==typ]
            if len(matches)==1:d['settings'][field]=matches[0]['pin'];status='Remapped documented equivalent'
            else:del d['settings'][field];status='Needs connection'
            rows.append(dict(device=d['name'],field=field,status=status))
        for field in ('pullup_resistor','pid_kp','pid_ki','pid_kd','custom_curve','current_rating_rms'):d['settings'].pop(field,None)
    # Keep semantic definitions/overrides; selection compatibility is unresolved.
    catalog.validate(result)
    return dict(draft=result,changes=rows,identity_cleared=True)


def runtime_assets(draft,catalog):
    boards=[]
    for role,selection in sorted(draft['boards'].items()):
        if 'id' not in selection:continue
        original=catalog.boards[selection['id']];b=compact_mapping(original)
        profiles={d.get('profile') for d in draft['devices'] if d['board']==role}
        b['presets']=[p for p in original.get('presets',[]) if p['id'] in profiles]
        boards.append(b)
    curves={'sovol-bed','sovol-hotend'}|{d['settings'].get('curve') for d in apply_inputs(draft,catalog)['devices'] if d['kind']=='sensor'}
    curves.update(d['settings'].get('curve') for b in boards for p in b.get('presets',[]) for d in p['devices'] if d['kind']=='sensor')
    return dict(format_version=1,boards=boards,curves=[copy.deepcopy(catalog.curves[c]) for c in sorted(curves-{None})],kinds=copy.deepcopy(catalog.kinds))


def locked_catalog(draft,catalog):
    assets=draft.get('definition_plan',{}).get('runtime_assets')
    if not assets:return catalog
    from sv08_printer_catalog import Catalog
    candidate=object.__new__(Catalog);candidate.data=copy.deepcopy(assets);candidate.supported=True
    candidate.validate_catalog();candidate.revision=digest(candidate.data)
    # Curves chosen later by the owner are instance overrides, resolved explicitly
    # from the installed runtime, then pinned at Save by PrinterStore.
    for d in draft['devices']:
        cid=d['settings'].get('curve')
        if cid and cid not in candidate.curves:raise ValueError('Sensor override requires updated runtime lock before generation')
    return candidate
