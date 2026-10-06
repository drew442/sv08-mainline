'use strict';
(() => {
    const $ = id => document.getElementById('printer-' + id);
    let catalog, draft, revision, loadedIdentity, saved, review, busy = false, epoch = 0, statusEpoch = 0, loading = false, changed = false, reconcile = false, diagnostic = false;
    const copy = value => JSON.parse(JSON.stringify(value));
    const notice = text => { $('notice').textContent = text; };
    const invalidate = (status = true) => { review = null; publicationReview=null; pendingDefinition=null; ++epoch; if (status) ++statusEpoch; if ($('candidate-review').open) $('candidate-review').close(); if ($('board-change').open) $('board-change').close(); for(const id of ['definition-review','publication-dialog'])if($(id).open)$(id).close(); };
    const edit = () => { changed = true; invalidate(); controls(); notice('Unsaved selections. Save draft before reviewing.'); };
    const authority = () => window.sv08Session?.available && window.sv08Session.elevated;
    function controls() {
        for (const id of ['save','review','restore','add','add-preset','apply','import']) $(id).disabled = busy || reconcile || diagnostic || !authority() || (!draft && id !== 'import');
        for (const field of document.querySelectorAll('#printer-components input, #printer-components select, #printer-components button, #printer-sensors select, #printer-boards input, #printer-boards select, #printer-boards button, #printer-devices input, #printer-devices select, #printer-devices button, #printer-calibration input, #printer-geometry-fields input, #printer-device-board, #printer-device-kind, #printer-device-name, #printer-device-preset, #printer-mode, #printer-cancel-import')) field.disabled = busy || reconcile || diagnostic || !authority();
        for(const id of ['custom-save','source-preview','source-import','migration-preview','publication-review','publication-reconcile','publication-restore-review','publication-apply','definition-confirm'])$(id).disabled=busy||reconcile||diagnostic||!authority();
        $('source-confirm').disabled=busy||reconcile||diagnostic||!authority()||!sourcePreview;
        $('add-preset').disabled ||= !$('device-preset').value;
        $('review').disabled ||= !draft;
        $('apply').disabled ||= !review?.complete || changed;
        $('restore').disabled ||= !saved?.previous;
        $('reconciliation').hidden = !(reconcile || diagnostic);
        $('reconcile').disabled = $('discard').disabled = busy || !authority();
    }
    async function rpc(request) {
        if (!authority()) throw new Error('Administrator access is required.');
        if (request.action !== 'status') request = {...request, expected_identity: loadedIdentity};
        const status = request.action === 'status', attempt = status ? statusEpoch : epoch;
        const proc = cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_printer_helper.py'], {superuser:'require',err:'message'});
        proc.input(JSON.stringify(request));
        let raw;
        try { raw = await proc; } catch (error) { if (['save','apply','restore','publication_apply','publication_reconcile','source_add','source_disable','source_enable','source_remove','publication_restore'].includes(request.action)) reconcile = true; throw error; }
        if (!authority() || attempt !== (status ? statusEpoch : epoch)) { if (['save','apply','restore','publication_apply','publication_reconcile','source_add','source_disable','source_enable','source_remove','publication_restore'].includes(request.action)) reconcile = true; throw new Error('Session or selections changed. Reconcile saved configuration; submitted operations may have completed.'); }
        const reply = JSON.parse(raw);
        if (!reply.ok) throw new Error(reply.error);
        return reply.result;
    }
    async function operation(fn) {
        if (busy) return; busy = true; controls();
        try { await fn(); }
        catch (e) { invalidate(); notice(e.message + (reconcile ? ' Reload to reconcile before retrying.' : '')); }
        finally { busy = false; controls(); if(catalog&&draft&&!diagnostic){renderDefinitionChoices();renderSources();} }
    }
    function el(tag,text) { const e=document.createElement(tag); if (text !== undefined) e.textContent=text; return e; }
    function select(options,value,onchange) {
        const e=el('select');
        for (const [v,label] of options) {const o=el('option',label);o.value=v;e.append(o);}
        e.value=value ?? '';e.addEventListener('change',()=>onchange(e.value));return e;
    }
    function label(text,control) {const e=el('label',text);e.append(control);return e;}
    function field(text,type,value,onchange,options) {
        let control;
        if (options) control=select([['','Unknown / choose explicitly'],...options],value,onchange);
        else if(type==='boolean') control=select([['','Unknown / choose explicitly'],['true','Yes'],['false','No']],value===undefined?'':String(value),v=>onchange(v===''?undefined:v==='true'));
        else {control=el('input');control.type=['text','ratio'].includes(type)?'text':'number';if(control.type==='number')control.step='any';control.value=value??'';control.addEventListener('change',()=>onchange(control.value===''?undefined:control.type==='number'?Number(control.value):control.value));}
        return label(text,control);
    }
    function boardData(role) {return catalog.boards.find(b=>b.id===draft.boards[role]?.id);}
    function presetPreview() {
        const preset=boardData($('device-board').value)?.presets?.find(p=>p.id===$('device-preset').value);
        const box=$('preset-preview');box.replaceChildren();
        if(preset){
            box.append(el('p',preset.notes),el('p','Configured reference polarity and circuit settings are not physically measured. Physical motor RMS rating remains unknown. Adds the named devices below; existing names or pins refuse the whole addition.'));
            const details=el('details');details.append(el('summary','Preview defaults and exact sources'));
            for(const device of preset.devices){
                details.append(el('strong',device.name+' · '+device.kind));
                for(const [key,value] of Object.entries(device.settings)){
                    const source={...boardData($('device-board').value).source,...device.sources[key]};details.append(el('p',key.replaceAll('_',' ')+': '+value+' — '+source.path+':'+source.line+' ['+source.section+'] '+source.option+' @ '+source.revision+'; accessed '+source.accessed));
                }
            }
            box.append(details);
        }else box.append(el('p','Choose a board, then a source-qualified component reference.'));
        controls();
    }
    function renderPresets() {
        const options=boardData($('device-board').value)?.presets??[];
        const selected=$('device-preset').value;$('device-preset').replaceChildren();
        const empty=el('option','Choose documented component');empty.value='';$('device-preset').append(empty);
        for(const p of options){const o=el('option',p.label);o.value=p.id;$('device-preset').append(o);}
        $('device-preset').value=options.some(p=>p.id===selected)?selected:'';presetPreview();
    }
    function renderBoards() {
        const expanded=Object.fromEntries([...$('boards').querySelectorAll('details[data-role]')].map(d=>[d.dataset.role,d.open]));
        $('boards').replaceChildren();
        for(const role of ['main','tool',...(draft.boards.chamber?['chamber']:[])]) {
            const box=el('fieldset');box.append(el('legend',({main:'Mainboard',tool:'Toolhead board',chamber:'Chamber module connection'})[role]));
            const board=boardData(role), selection=draft.boards[role]??{};
            const choice=select([['','Choose board reference'],...catalog.boards.filter(b=>b.role===role&&(advancedMode||['sv08-main','sv08-tool'].includes(b.id)||b.id===selection.id)).map(b=>[b.id,b.label])],selection.id, value=>{
                if(value===selection.id)return;
                const planned = value&&selection.id ? rpc({action:'board_preview',draft,role,board:value,expected_revision:revision}) : Promise.resolve({draft:{...copy(draft),boards:{...copy(draft.boards),[role]:value?{id:value}:{}},devices:draft.devices.filter(d=>d.board!==role)},changes:[]});
                $('board-change').showModal();
                planned.then(p=>{$('board-change').querySelector('p').textContent='Controller identity cleared. Assignments: '+p.changes.map(c=>c.device+' '+c.status).join(', ')+'. Unrelated controllers preserved.';}).catch(e=>notice(e.message));
                $('confirm-board').onclick=()=>operation(async()=>{
                    const result=await planned;if(!authority())return;invalidate();draft=result.draft;if(!value)delete draft.boards[role];edit();$('board-change').close();render();
                });
                $('cancel-board').onclick=()=>{$('board-change').close();renderBoards();};
                $('board-change').oncancel=()=>{renderBoards();};
                choice.value=selection.id??'';
            });
            box.append(label('Board / revision',choice));
            if(board){
                const connection=el('details');connection.dataset.role=role;connection.open=expanded[role]??false;connection.append(el('summary','Connection setup and board details'));
                box.append(connection);
                connection.append(el('p',board.warning),el('small','Documented reference. Installed match: unknown. '+board.unknowns.join('; ')));
                connection.append(el('small',board.source.path+' @ '+board.source.revision+'; accessed '+board.source.accessed));
                connection.append(field('Transport','text',selection.transport,v=>{if(v)selection.transport=v;else delete selection.transport;delete selection.identity;edit();renderBoards();},[['serial','USB / serial'],['can','CAN']].filter(([value])=>!board.supported_transports||board.supported_transports.includes(value))));
                connection.append(field('Private MCU identity','text',selection.identity,v=>{if(v)selection.identity=v;else delete selection.identity;edit();}));
                connection.append(field('Use this reference provisionally','boolean',selection.reference_ack,v=>{if(v===undefined)delete selection.reference_ack;else selection.reference_ack=v;edit();}));
            }
            $('boards').append(box);
        }
    }
    const friendlyPreset = (preset, board) => preset.label.replace(/ · .*$/, '').replace('Bed heater + temperature sensor', board.id==='sv08-main'?'Stock SV08 heated bed':'Reference bed configuration').replace('Hotend + extruder motor / TMC2209 + sensor', board.id==='sv08-tool'?'Stock SV08 hotend and extruder':'Reference hotend configuration');
    async function chooseComponent(role, preset) {
        await operation(async()=>{
            invalidate();
            const result=await rpc({action:'component',draft,role,preset,expected_revision:revision});
            draft=result.draft;edit();render();
            notice(draft.devices.some(d=>d.kind==='sensor'&&!d.settings.curve)?'Bed selected. Choose the supplied sensor type before preparing a candidate; you can save the hardware choice now.':'Hardware settings filled in. Save your selections; calibration can be done later.');
        });
        renderComponents();controls();
    }
    function renderComponents() {
        const root=$('components');root.replaceChildren();
        for(const role of ['main','tool']) {
            const board=boardData(role);if(!board)continue;
            const box=el('div');box.append(el('h3',role==='main'?'Mainboard components':'Toolhead components'));
            for(const kind of ['bed','extruder']) {
                const presets=(board.presets??[]).filter(p=>p.id!=='funssor_cn3d_bed').filter(p=>p.devices.some(d=>d.kind===kind));
                if(!presets.length)continue;
                const target=draft.devices.find(d=>d.board===role&&d.kind===kind);
                const match=presets.find(p=>p.id===target?.profile)??presets.find(p=>p.devices.every(expected=>draft.devices.some(d=>d.board===role&&d.name===expected.name&&d.kind===expected.kind&&Object.entries(expected.settings).every(([k,v])=>d.settings[k]===v))));
                const choice=select([['',target?'Current configuration (modified)':'Choose installed component'],...presets.map(p=>[p.id,friendlyPreset(p,board)])],match?.id??'',value=>{if(value)chooseComponent(role,value);});
                choice.dataset.component=kind;choice.dataset.board=role;
                box.append(label(kind==='bed'?'Heated bed':'Hotend',choice));
            }
            for(const preset of (board.presets??[]).filter(p=>p.devices.length===1&&p.devices[0].kind==='fan')) {
                const device=preset.devices[0], present=draft.devices.find(d=>d.board===role&&d.name===device.name&&d.kind==='fan');
                const toggle=el('input');toggle.type='checkbox';toggle.checked=!!present;toggle.dataset.component=preset.id;toggle.dataset.board=role;
                toggle.onchange=()=>{
                    if(toggle.checked)chooseComponent(role,preset.id);
                    else {draft.devices=draft.devices.filter(d=>d!==present);edit();render();}
                };
                box.append(label(preset.id==='exhaust_fan'?'Enclosure exhaust fan':friendlyPreset(preset,board),toggle));
            }
            root.append(box);
        }
        if(!root.children.length)root.append(el('p','Choose a mainboard and toolhead board to see supported components.'));
        const module=null; // Third-party add-ons are admitted through Definition sources.
        if(module) {
            const box=el('div');box.append(el('h3','Chamber heating'));
            const toggle=el('input');toggle.type='checkbox';toggle.dataset.component='chamber_module';toggle.dataset.board='chamber';
            toggle.checked=draft.boards.chamber?.id===module.id&&draft.devices.some(d=>d.board==='chamber'&&d.kind==='chamber');
            toggle.onchange=()=>{
                if(!toggle.checked){delete draft.boards.chamber;draft.devices=draft.devices.filter(d=>d.board!=='chamber');edit();render();return;}
                operation(async()=>{
                    invalidate();const selection=copy(draft);
                    if(selection.boards.chamber?.id!==module.id)selection.boards.chamber={id:module.id,transport:'can'};
                    const result=await rpc({action:'component',draft:selection,role:'chamber',preset:'chamber_module',expected_revision:revision});
                    draft=result.draft;edit();render();notice('Chamber module selected. Set up its CAN connection before preparing a candidate.');
                }).then(()=>{renderComponents();controls();});
            };
            box.append(label('Sovol SV08 MAX chamber heating module',toggle));
            box.append(el('p','Uses the module’s own CAN controller. Original SV08 installations need a confirmed CAN adapter and compatible module firmware.'));
            root.append(box);
        }
    }
    function renderSensors() {
        const root=$('sensors');root.replaceChildren();
        for(const device of draft.devices.filter(d=>d.kind==='sensor')) {
            const current=catalog.curves.find(c=>c.id===device.settings.curve);
            const box=el('div');box.append(el('p',device.name.replaceAll('_',' ')+' · Current sensor: '+(current?.label??'Not selected')));
            const choice=select([['','Choose replacement sensor'],...catalog.curves.map(c=>[c.id,c.label])],device.settings.curve,value=>{
                if(!value||value===device.settings.curve)return;
                const curve=catalog.curves.find(c=>c.id===value), board=boardData(device.board);
                // Bias belongs to the board input circuit, not the replacement curve.
                const reference=(board.presets??[]).flatMap(p=>p.devices).find(d=>d.kind==='sensor'&&d.settings.pin===device.settings.pin);
                device.settings.curve=value;
                delete device.settings.pullup_resistor;delete device.settings.custom_curve;
                if(reference)device.settings.pullup_resistor=reference.settings.pullup_resistor;
                // Keep existing heater temperature protections; do not raise bounds.
                for(const heater of draft.devices.filter(d=>d.settings.sensor===device.name))
                    for(const key of ['pid_kp','pid_ki','pid_kd'])delete heater.settings[key];
                edit();render();
                notice('Sensor changed to '+curve.label+'. Board input defaults restored; heater PID calibration can be done later.'+(reference?'':' Set the input bias in advanced settings for this custom connection.'));
            });
            choice.dataset.sensor=device.name;box.append(label('Temperature sensor',choice));root.append(box);
        }
        if(!root.children.length)root.append(el('p','Select a heated bed or hotend to configure its sensor.'));
    }
    function renderDevices() {
        $('devices').replaceChildren();
        for(const device of draft.devices) {
            const box=el('fieldset');box.append(el('legend',device.name+' · '+device.kind+' · '+device.board));
            const remove=el('button','Remove device');remove.onclick=()=>{draft.devices=draft.devices.filter(d=>d!==device);edit();render();};box.append(remove);
            const board=boardData(device.board), settings=el('div'), advanced=el('details');settings.className='settings';advanced.append(el('summary','Advanced electrical and motion fields'));

            if(!board){box.append(el('p','Choose a board first'));$('devices').append(box);continue;}
            box.append(el('small','Configured selections; physical identity, measured polarity and circuit limits remain unverified. Motor RMS rating requires an explicit owner value.'));
            const references=(board.presets??[]).filter(p=>p.devices.some(d=>d.name===device.name&&d.kind===device.kind));
            if(references.length){
                const origin=el('details');origin.append(el('summary','Available documented defaults and origins'));
                for(const p of references){origin.append(el('p',p.label+'. '+p.notes));
                    for(const d of p.devices.filter(d=>d.name===device.name&&d.kind===device.kind))for(const [key,value] of Object.entries(d.settings)){
                        const source={...board.source,...d.sources[key]};origin.append(el('p',key.replaceAll('_',' ')+': reference '+value+' — '+source.path+':'+source.line+' @ '+source.revision+'; accessed '+source.accessed));
                    }
                }box.append(origin);
            }
            for(const [name,type] of Object.entries(catalog.kinds[device.kind])) {
                if(name==='custom_curve'||name.startsWith('pid_'))continue;
                let options;
                if(['adc','input','probe','heater','fan'].includes(type)) {
                    options=Object.entries(board.signals).filter(([,s])=>s.capabilities.includes(type)&&!s.reserved).map(([p])=>{
                        const c=Object.values(board.connectors).find(c=>c.pin===p&&c.capability===type);
                        return [p,(c?.label??'Reference signal')+' → '+(device.board==='main'?'':device.board+':')+p+(c?.contact?' ('+c.contact+')':' (contact unknown)')];
                    });
                } else if(type==='motor') options=Object.entries(board.motors).map(([n,p])=>[n,n+' → '+Object.entries(p).map(([k,p])=>k+':'+p).join(', ')]);
                else if(type==='curve')options=catalog.curves.map(c=>[c.id,c.label]);
                else if(type==='name')options=draft.devices.filter(d=>d.kind==='sensor'&&d.board===device.board).map(d=>[d.name,d.name]);
                else if(type==='control')options=[['pid','PID (enter gains)'],['watermark','Watermark']];
                const text=({'invert':'Invert signal','invert_dir':'Invert direction','invert_enable':'Invert enable','digital_pullup':'Digital input pull-up','pullup_resistor':'Analog pull-up resistance (ohm)','current_rating_rms':'Motor RMS rating (A), owner entered','run_current':'Driver RMS current (A)','sense_resistor':'Sense resistor (ohm), explicit','pin':'Connection / pin'}[name]??name.replaceAll('_',' '));
                advanced.append(field(text,type==='name'?'text':type,device.settings[name],value=>{
                    if(value===undefined||value==='')delete device.settings[name];else device.settings[name]=value;
                    if(device.kind==='sensor'&&['curve','pullup_resistor'].includes(name))for(const heater of draft.devices.filter(d=>d.settings.sensor===device.name))for(const key of ['pid_kp','pid_ki','pid_kd'])delete heater.settings[key];
                    if(name==='curve'){delete device.settings.custom_curve;delete device.settings.pullup_resistor;delete device.settings.min_temp;delete device.settings.max_temp;}
                    if(name==='connector')for(const key of ['invert_dir','invert_enable','run_current','current_rating_rms','sense_resistor','uart_address','endstop_pin','endstop_invert','endstop_pullup'])delete device.settings[key];
                    if(name==='control' && value!=='pid')for(const key of ['pid_kp','pid_ki','pid_kd'])delete device.settings[key];
                    edit();renderSensors();renderComponents();renderCalibration();if(['curve','connector','control'].includes(name))renderDevices();
                },options));
            }
            box.append(settings);if(advanced.querySelector('label'))box.append(advanced);
            if(device.kind==='sensor') {
                const curve=catalog.curves.find(c=>c.id===device.settings.curve);
                if(curve){
                    if(curve.sensor_type!=='PT1000') {
                        const custom=el('details');custom.append(el('summary','Custom NTC calibration curve'));
                        custom.append(el('p','Enter three temperature / resistance pairs. Leave this closed to use the sensor’s default curve.'));
                        const points=copy(device.settings.custom_curve??curve.points??[[null,null],[null,null],[null,null]]);
                        for(let i=0;i<3;i++)for(const [j,title] of [[0,'Temperature (°C)'],[1,'Resistance (ohm)']])
                            custom.append(field(title+' '+(i+1),'number',points[i][j],v=>{points[i][j]=v;}));
                        const use=el('button','Use custom curve');use.onclick=()=>{
                            if(!points.every(p=>p.every(v=>typeof v==='number'&&Number.isFinite(v)))){notice('Enter all three temperature / resistance pairs.');return;}
                            device.settings.custom_curve=copy(points);
                            for(const heater of draft.devices.filter(d=>d.settings.sensor===device.name))for(const key of ['pid_kp','pid_ki','pid_kd'])delete heater.settings[key];
                            edit();render();
                        };
                        const reset=el('button','Use default sensor curve');reset.onclick=()=>{delete device.settings.custom_curve;for(const heater of draft.devices.filter(d=>d.settings.sensor===device.name))for(const key of ['pid_kp','pid_ki','pid_kd'])delete heater.settings[key];edit();render();};
                        custom.append(use,reset);box.append(custom);
                    }
                    box.append(el('small',curve.origin+'. '+curve.pullup_origin+'. Physical sensor/circuit identity unknown.'));
                    if(curve.reference_bounds)box.append(el('small',curve.bounds_origin+': '+curve.reference_bounds.join(' to ')+' °C.'));
                    const preset=el('button',curve.reference_bounds?'Use factory configured pull-up and bounds':'Use documented reference pull-up');
                    preset.onclick=()=>{device.settings.pullup_resistor=curve.reference_pullup;if(curve.reference_bounds){[device.settings.min_temp,device.settings.max_temp]=curve.reference_bounds;}for(const heater of draft.devices.filter(d=>d.settings.sensor===device.name))for(const key of ['pid_kp','pid_ki','pid_kd'])delete heater.settings[key];edit();renderCalibration();renderDevices();};box.append(preset);
                }
            }
            $('devices').append(box);
        }
    }
    function renderCalibration() {
        const root=$('calibration');root.replaceChildren();
        for(const heater of draft.devices.filter(d=>['bed','extruder'].includes(d.kind))) {
            const box=el('fieldset');box.append(el('legend',heater.name.replaceAll('_',' ')));
            for(const key of ['pid_kp','pid_ki','pid_kd'])box.append(field(key.replaceAll('_',' '),'positive',heater.settings[key],value=>{if(value===undefined)delete heater.settings[key];else heater.settings[key]=value;edit();}));
            root.append(box);
        }
    }
    function render() {
        renderBoards();renderComponents();renderSensors();renderDevices();renderPresets();renderCalibration();$('geometry-fields').replaceChildren();
        for(const key of ['max_velocity','max_accel','max_z_velocity','max_z_accel'])$('geometry-fields').append(field(key.replaceAll('_',' '),'positive',draft.geometry[key],v=>{if(v===undefined)delete draft.geometry[key];else draft.geometry[key]=v;edit();}));
        $('current').textContent=saved.current?'Candidate saved — inactive ('+saved.current.mode+'). Commissioning and activation require separate reviewed steps.':'No saved candidate.';
        controls();renderDesign();
    }
    // Route changes cancel reviews, but a read-only load may finish in either panel.
    async function load(keep = false) {
        loading=true;
        try {
            invalidate();const result=await rpc({action:'status'});loadedIdentity=result.loaded_identity;catalog=result.catalog;saved=result.state;definitionRows=result.definitions??[];sourceRows=result.sources??{};const filters=$('definition-filter');const selectedFilter=filters.value;filters.replaceChildren();for(const [v,t] of [['','All sources'],['builtin','Built-in'],...Object.values(sourceRows).map(s=>[s.id,s.repository??s.manifest.name])]){const o=el('option',t);o.value=v;filters.append(o);}filters.value=selectedFilter;revision=saved.revision;if (!keep || !draft) { draft=saved.draft===undefined?null:copy(saved.draft);changed=false; } reconcile=false;diagnostic=false;
            if(saved.format_version!==1 || saved.draft?.format_version!==1 || result.catalog_supported===false){notice('Unsupported stored schema or catalog. Export for diagnosis; editing is disabled.');diagnostic=true;$('export').textContent=draft?.format_version===1&&draft.boards?'Export retained local draft':'Export private diagnostic backup';controls();return;}
            if(catalog.boards.some(b=>b.role==='chamber')&&!$('device-board').querySelector('[value=chamber]')){const o=el('option','Chamber module');o.value='chamber';$('device-board').append(o);}
            $('device-kind').replaceChildren();for(const kind of Object.keys(catalog.kinds)){const o=el('option',kind);o.value=kind;$('device-kind').append(o);}
            $('export').textContent='Export shareable draft';$('import-diff').hidden=true;render();notice('Saved configuration loaded. Candidates remain inactive.');
        } finally { loading=false; }
    }
    // Component-first presentation over the same instance state and RPC authority.
    let localView='components', selectedCategory=null, advancedMode=false, definitionRows=[], sourceRows={}, sourcePreview=null, pendingDefinition=null, publicationReview=null, mapMode=true, selectedConnection=null;
    const categories=[['bed','Bed & build surface','M4 17h20M5 13l11-5 11 5-11 5zM8 5V2m8 3V2m8 3V2'],['probe','Probe & levelling','M12 3h8v15l-4 5-4-5zM5 28h22'],['toolhead','Toolhead & extrusion','M8 4h16v10H8zM11 14h10v7l-5 7-5-7zM4 9h4m16 0h4'],['filament','Filament & multi-colour','M4 4h10v24H4zM18 4h10v24H18zM9 10h0m14 0h0M9 20h14'],['boards','Boards & connections','M6 6h20v20H6zM11 11h10v10H11zM2 10h4m20 0h4M2 22h4m20 0h4'],['cooling','Cooling & enclosure','M16 13c-13-15-13 9 0 3m3 0c15-13-9-13-3 0m0 3c13 15 13-9 0-3m-3 0c-15 13 9 13 3 0'],['motion','Motion & endstops','M3 25L25 3M3 8V3h5M24 29h5v-5']];
    function categoryFor(device){if(['bed'].includes(device.kind)||/bed/.test(device.name))return 'bed';if(device.kind==='probe')return 'probe';if(device.kind==='extruder'||device.board==='tool'&&/hotend|extruder/.test(device.name))return 'toolhead';if(device.kind==='motor')return 'motion';if(device.kind==='input')return 'filament';if(['fan','chamber'].includes(device.kind)||device.board==='chamber')return 'cooling';return 'boards';}
    function setView(view){localView=view;for(const name of ['components','connections','changes','sources'])$(name==='sources'?'sources-view':name+'-view').hidden=name!==view;for(const b of document.querySelectorAll('[data-printer-view]'))b.setAttribute('aria-current',b.dataset.printerView===view?'page':'false');$('history-panel').hidden=true;if(view==='connections')renderConnections();if(view==='changes')renderChanges();if(view==='sources')renderSources();}
    function renderDesign(){
        $('board-summary').textContent=Object.entries(draft.boards).map(([role])=>boardData(role)?.label??'Unknown '+role).join(' · ')||'Boards not selected';
        const root=$('cards');root.replaceChildren();
        for(const [key,title,path] of categories){
            const devices=draft.devices.filter(d=>categoryFor(d)===key), refs=(draft.definition_plan?.selections??[]).filter(r=>draft.definition_plan.snapshots[r.source+'::'+r.id+'@'+r.version]?.category===key);
            const b=el('button');b.className='printer-card';b.dataset.category=key;b.setAttribute('aria-current',String(key===selectedCategory));
            const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 32 32');svg.setAttribute('aria-hidden','true');const p=document.createElementNS(svg.namespaceURI,'path');p.setAttribute('d',path);svg.append(p);
            const text=el('span');text.append(el('strong',title),el('small',refs.map(r=>draft.definition_plan.snapshots[r.source+'::'+r.id+'@'+r.version].name).join(', ')||devices.map(d=>d.name.replaceAll('_',' ')).join(', ')||(key==='boards'?'Configure controller references':'Not specified')));
            const missing=devices.some(d=>d.kind==='sensor'&&!d.settings.curve),status=el('span',missing?'Needs sensor':devices.length?'Selections available':'Not specified');status.className='printer-status'+(missing?' needs':'');text.append(status);b.append(svg,text);b.onclick=()=>{selectedCategory=key;renderDesign();renderDefinitionChoices();$('detail-title').focus();};root.append(b);
        }
        $('detail-panel').hidden=!selectedCategory;$('detail-title').textContent=categories.find(c=>c[0]===selectedCategory)?.[1]??'';$('detail-title').tabIndex=-1;
        $('boards').hidden=selectedCategory!=='boards';$('advanced').hidden=!advancedMode;$('advanced').open=advancedMode;
        // Existing structured controls remain scoped to their contextual category.
        for(const box of $('components').children){const role=box.querySelector('[data-board]')?.dataset.board;box.hidden=!advancedMode&&selectedCategory!=='cooling' || role==='tool'&&selectedCategory==='bed';}
        for(const box of $('sensors').children){const name=box.querySelector('[data-sensor]')?.dataset.sensor;const d=draft.devices.find(d=>d.name===name);box.hidden=!d||categoryFor(d)!==selectedCategory;}
        for(const box of $('devices').children){const legend=box.querySelector('legend')?.textContent;const d=draft.devices.find(d=>legend?.startsWith(d.name+' ·'));box.hidden=!d||categoryFor(d)!==selectedCategory;}
        $('custom-config').value=draft.custom_config??'';
        $('selection-status').textContent=changed?'Unsaved component selections':'Selections saved · configuration and commissioning separate';renderChanges();renderDefinitionChoices();
        if(localView==='connections')renderConnections();
    }
    function renderDefinitionChoices(){
        const root=$('definition-choices');root.replaceChildren();const search=$('definition-search').value.toLowerCase(),filter=$('definition-filter').value;
        for(const row of definitionRows){const d=row.record;if(d.category!==selectedCategory||filter&&row.reference.source!==filter||search&&!([d.name,...d.aliases??[]].join(' ').toLowerCase().includes(search)))continue;
            const compatible=d.kind==='board'||(d.compatibility.boards??[]).every(id=>Object.values(draft.boards).some(b=>b.id===id));
            const b=el('button');b.className='printer-choice';b.append(el('strong',d.name),el('small',row.origin+' · '+d.version),el('small',compatible?'Documented defaults; instance details remain local':'Choose a compatible board first'));b.disabled=!compatible||!authority()||busy||diagnostic||reconcile;b.onclick=()=>operation(async()=>{invalidate();const result=await rpc({action:'definition',draft,reference:row.reference,expected_revision:revision});if(d.components?.length===1&&d.components[0].kind==='fan'&&!d.dependencies?.length&&!d.behaviours?.length){draft=result.draft;edit();render();notice('Fan settings added to your selections. Save when ready.');return;}pendingDefinition=result.draft;const before=draft.devices.map(d=>d.name);$('definition-effects').textContent=d.name+'\n'+d.description+'\n\nDevices: '+result.draft.devices.map(d=>d.name).join(', ')+'\nPrevious: '+before.join(', ')+'\nCalibration for replaced hardware is cleared. Nothing is saved or applied.';$('definition-review').showModal();$('definition-cancel').focus();});root.append(b);
        }
        for(const ref of draft.definition_plan?.selections??[]){const d=draft.definition_plan.snapshots[ref.source+'::'+ref.id+'@'+ref.version];if(d.category!==selectedCategory)continue;for(const [key,inp] of Object.entries(d.inputs??{})){if(inp.type==='curve')continue;const value=draft.definition_plan.instance_values?.[inp.target];root.append(field(inp.label,inp.type==='identity'||inp.type==='choice'?'text':inp.type==='boolean'?'boolean':'number',value,v=>{draft.definition_plan.instance_values??={};if(v===undefined)delete draft.definition_plan.instance_values[inp.target];else draft.definition_plan.instance_values[inp.target]=v;edit();},inp.type==='choice'?(inp.choices??[]).map(v=>[String(v),String(v)]):undefined));}for(const gap of d.unresolved??[])root.append(el('p','Definition incomplete: '+gap));root.append(el('small','Selected '+ref.version+' · '+ref.source+' · user-declared installation'));
            const guide=el('details');guide.append(el('summary','Defaults, overrides and sources'));
            for(const c of d.components??[]){const actual=draft.devices.find(x=>x.name===c.name&&x.board===c.board);if(!actual)continue;for(const [key,value] of Object.entries(c.settings)){const row=el('p',c.name+' · '+key.replaceAll('_',' ')+': '+JSON.stringify(actual.settings[key])+' · '+(JSON.stringify(value)===JSON.stringify(actual.settings[key])?'Definition default':'Local override'));if(JSON.stringify(value)!==JSON.stringify(actual.settings[key])){const reset=el('button','Reset to definition default');reset.disabled=!authority()||busy||reconcile;reset.onclick=()=>{actual.settings[key]=copy(value);for(const gain of ['pid_kp','pid_ki','pid_kd'])delete actual.settings[gain];edit();render();};row.append(reset);}guide.append(row);}}
            for(const source of d.sources){if(source.url){const a=el('a',source.id+' · '+source.locator);a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';guide.append(a);}else guide.append(el('p',source.revision+' · '+source.locator));}root.append(guide);
            const remove=el('button','Remove definition and owned contributions');remove.disabled=!authority()||busy||reconcile;remove.onclick=()=>operation(async()=>{const result=await rpc({action:'definition_remove',draft,reference:ref,expected_revision:revision});pendingDefinition=result.draft;$('definition-effects').textContent='Remove '+d.name+' and contributions not shared by retained definitions. Other configuration remains. Review: '+JSON.stringify(result.draft.devices.map(c=>c.name));$('definition-review').showModal();});root.append(remove);}
        if(!root.children.length)root.append(el('p','No matching supported definitions. Choose a board, add a source or use explicit structured settings in Advanced.'));
    }
    function renderChanges(){
        const root=$('semantic-changes');root.replaceChildren();let count=0;
        for(const [key,title] of categories){const before=saved.draft.devices.filter(d=>categoryFor(d)===key),after=draft.devices.filter(d=>categoryFor(d)===key);const refsFor=state=>(state.definition_plan?.selections??[]).filter(r=>state.definition_plan.snapshots[r.source+'::'+r.id+'@'+r.version]?.category===key);const beforeRefs=refsFor(saved.draft),afterRefs=refsFor(draft);if(JSON.stringify(before)===JSON.stringify(after)&&JSON.stringify(beforeRefs)===JSON.stringify(afterRefs))continue;count++;const box=el('div');box.className='printer-change';box.append(el('h3',title),el('p',(before.map(d=>d.name).join(', ')||'Unspecified')+' → '+(after.map(d=>d.name).join(', ')||'Removed')));for(const d of after){const prior=before.find(x=>x.name===d.name);for(const field of new Set([...Object.keys(prior?.settings??{}),...Object.keys(d.settings)])){const value=d.settings[field];if(JSON.stringify(prior?.settings[field])!==JSON.stringify(value))box.append(el('p',d.name+' · '+field.replaceAll('_',' ')+': '+(prior?.settings[field]??'Unknown')+' → '+(value===undefined?'Cleared / needs input':JSON.stringify(value))+' · effective instance value'));}if(d.kind==='sensor'&&!d.settings.curve)box.append(el('p','Needs your input: identify the fitted sensor.'));}if(JSON.stringify(beforeRefs)!==JSON.stringify(afterRefs))box.append(el('p','Definition: '+(beforeRefs.map(r=>r.source+' · '+r.id+' @ '+r.version).join(', ')||'Unassigned')+' → '+(afterRefs.map(r=>r.source+' · '+r.id+' @ '+r.version).join(', ')||'Removed')));for(const ref of afterRefs){const definition=draft.definition_plan.snapshots[ref.source+'::'+ref.id+'@'+ref.version];for(const gap of definition.unresolved??[])box.append(el('p','Definition incomplete: '+gap));for(const inp of Object.values(definition.inputs??{})){const [name,field]=inp.target.split('.');const actual=draft.devices.find(d=>d.name===name)?.settings[field]??draft.boards[name]?.[field]??draft.definition_plan.instance_values?.[inp.target]??inp.default;if(inp.required&&actual===undefined)box.append(el('p','Needs your input: '+inp.label));}}root.append(box);}
        if(JSON.stringify(draft.boards)!==JSON.stringify(saved.draft.boards)){count++;root.append(el('p','Controller references / connection identities changed.'))}
        if(!root.children.length)root.append(el('p','No pending component changes.'));
        $('change-count').textContent=String(count);
    }
    function renderConnections(){
        const filter=$('connection-filter').value.toLowerCase(), rows=[];
        for(const d of draft.devices){const board=boardData(d.board);if(!board)continue;for(const [field,value] of Object.entries(d.settings)){const type=catalog.kinds[d.kind][field];if(!['adc','heater','fan','probe','input','motor'].includes(type))continue;const connector=type==='motor'?{label:value,contact:null}:Object.values(board.connectors).find(c=>c.pin===value&&c.capability===type);rows.push({d,field,value,type,board,connector});}}
        const root=$('connection-map'),tableRoot=$('connection-table');root.replaceChildren();tableRoot.replaceChildren();root.hidden=!mapMode;tableRoot.hidden=mapMode;
        const table=el('table'),head=el('tr');for(const label of ['Board','Header','Contact','Signal / controller','Device'])head.append(el('th',label));const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');table.append(body);
        for(const row of rows){const values=[row.board.label,row.connector?.label??'Unresolved',row.connector?.contact??'Contact unknown',row.d.board+':'+row.value,row.d.name];if(filter&&!values.join(' ').toLowerCase().includes(filter))continue;const selectRow=()=>{selectedConnection=row;renderConnectionInspector();};const path=el('div');path.className='printer-connection-path';for(const text of [values[0],values[1]+' · '+values[2],values[3]])path.append(el('span',text));const button=el('button',values[4]);button.onclick=selectRow;path.append(button);root.append(path);const tr=el('tr');for(const text of values.slice(0,4))tr.append(el('td',text));const td=el('td'),b=el('button',values[4]);b.onclick=selectRow;td.append(b);tr.append(td);body.append(tr);}
        for(const [role,b] of Object.entries(draft.boards)){const line=el('p',role+' controller · '+(b.transport?.toUpperCase()??'Transport needed')+' · '+(b.identity?'Instance identity entered':'Identity needed'));root.append(line);}
        tableRoot.append(table);if(selectedConnection)renderConnectionInspector();
    }
    function renderConnectionInspector(){const root=$('connection-inspector');root.replaceChildren();const row=selectedConnection;if(!row)return;const d=draft.devices.find(d=>d.name===row.d.name);if(!d)return;root.append(el('h3',d.name.replaceAll('_',' ')+' connection'));const choices=row.type==='motor'?Object.keys(row.board.motors).map(k=>[k,k]):Object.entries(row.board.connectors).filter(([,c])=>c.capability===row.type).map(([k,c])=>[k,c.label+' · '+(c.contact??'Contact unknown')]);const value=row.type==='motor'?row.value:Object.keys(row.board.connectors).find(k=>row.board.connectors[k].pin===row.value&&row.board.connectors[k].capability===row.type);const f=field('Documented connector','text',value,v=>{d.settings[row.field]=row.type==='motor'?v:row.board.connectors[v].pin;for(const key of ['pid_kp','pid_ki','pid_kd','custom_curve'])d.settings[key]&&delete d.settings[key];edit();render();},choices);root.append(f,el('small','Signal derived from the selected board mapping. Physical contacts remain unknown where undocumented.'));}
    function renderSources(){const root=$('source-list');root.replaceChildren();const table=el('table'),body=el('tbody');table.append(body);const builtin=el('tr');for(const text of ['SV08 Mainline','Built-in','Available'])builtin.append(el('td',text));body.append(builtin);for(const source of Object.values(sourceRows)){const tr=el('tr');for(const text of [source.manifest.name,source.repository??'Local bundle',source.enabled?'Available':'Disabled'])tr.append(el('td',text));const td=el('td');for(const [label,action] of [['Check for updates','source_check'],[source.enabled?'Disable':'Enable',source.enabled?'source_disable':'source_enable'],['Remove','source_remove']]){const b=el('button',label);b.disabled=!authority()||busy||reconcile||action==='source_check'&&(!source.enabled||source.origin!=='github');b.onclick=()=>operation(async()=>{const r=await rpc({action,source_id:source.id,expected_revision:revision});if(action==='source_check'){sourcePreview=r;showSourcePreview();}else{await load(true);renderSources();notice('Subscription updated; selected locked definitions retained.');}});td.append(b);}tr.append(td);body.append(tr);}root.append(table);}
    function showSourcePreview(){const root=$('source-preview-detail');root.replaceChildren();if(!sourcePreview)return;root.append(el('h3',sourcePreview.manifest.name),el('p',(sourcePreview.repository??'Local bundle')+' · '+sourcePreview.commit),el('p','Publisher declaration: '+JSON.stringify(sourcePreview.manifest.publisher)+' · '+sourcePreview.manifest.license),el('p',sourcePreview.records.length+' supported · '+sourcePreview.unavailable.length+' unavailable'));for(const x of sourcePreview.unavailable)root.append(el('p',x.id+': '+x.reason));$('source-confirm').disabled=!authority();}
    for(const b of document.querySelectorAll('[data-printer-view]'))b.onclick=()=>setView(b.dataset.printerView);
    $('custom-save').onclick=()=>{if(!authority()||busy||reconcile)return;const value=$('custom-config').value;if(value)draft.custom_config=value;else delete draft.custom_config;edit();render();};
    $('detail-back').onclick=()=>{const key=selectedCategory;selectedCategory=null;renderDesign();$('cards').querySelector('[data-category='+key+']')?.focus();};
    $('definition-search').oninput=renderDefinitionChoices;$('definition-filter').onchange=renderDefinitionChoices;
    $('advanced-toggle').onchange=()=>{advancedMode=$('advanced-toggle').checked;renderBoards();renderDesign();};
    $('show-changes').onclick=()=>setView('changes');$('history').onclick=()=>{$('history-panel').hidden=!$('history-panel').hidden;};
    $('map-toggle').onclick=()=>{mapMode=true;renderConnections();};$('table-toggle').onclick=()=>{mapMode=false;renderConnections();};$('connection-filter').oninput=renderConnections;
    $('source-open').onclick=()=>setView('sources');$('source-back').onclick=()=>setView('components');
    $('definition-cancel').onclick=()=>{$('definition-review').close();pendingDefinition=null;};$('definition-confirm').onclick=()=>{if(!pendingDefinition||!authority()||busy||reconcile)return;draft=pendingDefinition;pendingDefinition=null;$('definition-review').close();edit();render();};
    $('source-preview').onclick=()=>operation(async()=>{sourcePreview=await rpc({action:'source_preview',url:$('source-url').value,ref:$('source-ref').value||null,path:$('source-path').value||null,expected_revision:revision});showSourcePreview();});
    $('source-import').onchange=()=>operation(async()=>{const file=$('source-import').files[0];if(!file)return;if(file.size>524288)throw Error('Bundle exceeds limit');sourcePreview=await rpc({action:'bundle_preview',bundle:JSON.parse(await file.text()),expected_revision:revision});showSourcePreview();});
    $('source-confirm').onclick=()=>operation(async()=>{if(!sourcePreview)return;await rpc({action:'source_add',source:sourcePreview,expected_revision:revision});sourcePreview=null;await load(true);renderSources();notice('Catalogue available. Selected definition snapshots and local selections unchanged.');});
    $('migration-preview').onclick=()=>operation(async()=>{const result=await rpc({action:'migration',expected_revision:revision});$('migration-detail').replaceChildren(el('p','Migration preserves a backup in memory; save only after reviewing exact profile matches and imported devices.'),el('pre',JSON.stringify(result.changes,null,2)));const use=el('button','Use migrated draft');use.onclick=()=>{draft=result.draft;edit();render();};$('migration-detail').append(use);});
    $('publication-review').onclick=()=>operation(async()=>{publicationReview=await rpc({action:'publication_review',expected_revision:revision});$('publication-detail').textContent=JSON.stringify(publicationReview.diff,null,2)+'\nPrinter remains stopped. Required calibration/commissioning is separate.';$('publication-dialog').showModal();});
    $('publication-cancel').onclick=()=>{$('publication-dialog').close();publicationReview=null;};$('publication-restore-review').onclick=()=>operation(async()=>{publicationReview=await rpc({action:'publication_restore_review',expected_revision:revision});publicationReview.restoration=true;$('publication-detail').textContent='Restore with printer stopped:\n'+publicationReview.before+'\n→\n'+(publicationReview.after??'No previous live configuration');$('publication-dialog').showModal();});
    $('publication-apply').onclick=()=>operation(async()=>{if(!publicationReview)return;const result=await rpc({action:publicationReview.restoration?'publication_restore':'publication_apply',expected_revision:revision,review:publicationReview.review});$('publication-dialog').close();publicationReview=null;await load();notice(result.message??'Prior configuration restored. Printer remains stopped; review against fitted hardware.');});$('publication-reconcile').onclick=()=>operation(async()=>{await rpc({action:'publication_reconcile',expected_revision:revision});await load();notice('Interrupted publication restored; review against fitted hardware before continuing.');});
    $('reload').onclick=()=>{ if (changed || reconcile) { reconcile=true; controls(); notice('Choose reconciliation to retain local selections, or explicitly discard them.'); } else operation(()=>load()); };
    $('reconcile').onclick=()=>operation(()=>load(true));
    $('discard').onclick=()=>{if(confirm('Discard unsaved printer selections?'))operation(()=>load());};
    $('device-board').onchange=renderPresets;
    $('device-preset').onchange=presetPreview;
    $('add-preset').onclick=()=>operation(async()=>{invalidate();const result=await rpc({action:'preset',draft,role:$('device-board').value,preset:$('device-preset').value,expected_revision:revision});draft=result.draft;edit();render();notice('Reference defaults added to unsaved draft. Inspect settings; physical identity, motor ratings and measured polarity remain unverified. Save may remain incomplete.');});
    $('add').onclick=()=>{const role=$('device-board').value,name=$('device-name').value;if(!boardData(role)){notice('Choose a board reference first.');return;}if(!/^[a-z][a-z0-9_]{0,39}$/.test(name)||draft.devices.some(d=>d.name===name)){notice('Use a unique lowercase device name.');return;}draft.devices.push({name,board:role,kind:$('device-kind').value,settings:{}});edit();renderDevices();};
    $('save').onclick=()=>operation(async()=>{const result=await rpc({action:'save',expected_revision:revision,draft});revision=result.revision;changed=false;invalidate();await load();notice(result.message);});
    $('mode').onchange=()=>{invalidate();controls();};
    $('review').onclick=()=>operation(async()=>{review=await rpc(changed?{action:'review_draft',draft,mode:$('mode').value,expected_revision:revision}:{action:'review',mode:$('mode').value});$('output-diff').replaceChildren(el('h3','Actual inactive candidate text'),el('pre','Previous:\n'+(saved.current?.text??'(none)')+'\nCandidate:\n'+(review.text??'Not emitted: incomplete settings')));$('review-detail').textContent=[...review.blockers,...review.warnings].join('\n');$('review-text').textContent=review.text??'';$('candidate-review').showModal();$('cancel-review').focus();});
    $('cancel-review').onclick=()=>{invalidate();controls();};$('candidate-review').oncancel=()=>{invalidate();controls();};
    $('apply').onclick=()=>operation(async()=>{const result=await rpc({action:'apply',mode:$('mode').value,review:review.review});invalidate();await load();notice(result.message+' — use the commissioning handoff before activation.');});
    $('restore').onclick=()=>operation(async()=>{await rpc({action:'restore',expected_revision:revision});await load();notice('Previous candidate draft restored. Review before applying.');});
    function download(name,text,type) {const url=URL.createObjectURL(new Blob([text],{type}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    $('export').onclick=()=>{const shareable=draft?.format_version===1&&draft.boards&&draft.devices;download(shareable?'printer-hardware-draft.json':'printer-hardware-diagnosis.json',JSON.stringify(shareable?{...draft,boards:Object.fromEntries(Object.entries(draft.boards).map(([role,b])=>[role,{...b,identity:undefined}])),definition_plan:draft.definition_plan?{...draft.definition_plan,instance_values:Object.fromEntries(Object.entries(draft.definition_plan.instance_values??{}).filter(([k])=>!k.endsWith('.identity')))}:undefined,custom_config:draft.custom_config?'# Custom text omitted from shareable export; use private backup separately':undefined}:{state:saved,catalog},null,2),'application/json');};
    $('export-config').onclick=()=>{if(saved?.current)download('inactive-candidate.cfg',saved.current.text,'text/plain');else notice('No saved candidate to export.');};
    function showImportDiff(before,after) {
        const rows=$('import-diff-rows');rows.replaceChildren();
        function walk(a,b,path) {
            if(JSON.stringify(a)===JSON.stringify(b))return;
            if((a && typeof a==='object') || (b && typeof b==='object')) {
                for(const key of new Set([...Object.keys(a??{}),...Object.keys(b??{})]))walk(a?.[key],b?.[key],path?path+'.'+key:key);
            } else {
                const tr=el('tr');for(const value of [path.replaceAll('_',' '),a===undefined?'Not set':String(a),b===undefined?'Not set':String(b)])tr.append(el('td',value));rows.append(tr);
            }
        }
        walk(before,after,'');$('import-diff').hidden=false;
        if(!rows.children.length){const tr=el('tr');const td=el('td','No changes');td.colSpan=3;tr.append(td);rows.append(tr);}
    }
    $('cancel-import').onclick=()=>{invalidate();draft=saved.draft===undefined?null:copy(saved.draft);changed=false;$('import-diff').hidden=true;render();notice('Imported changes discarded. Saved draft preserved.');};
    $('import').onchange=()=>operation(async()=>{invalidate();$('import-diff').hidden=true;const file=$('import').files[0];if(!file)return;$('import').value='';if(file.size>131072)throw new Error('Import exceeds 128 KiB.');const incoming=JSON.parse(await file.text());const result=await rpc({action:'import',draft:incoming,expected_revision:revision});draft=result.draft;changed=true;render();showImportDiff(saved.draft,draft);notice(result.changed?'Imported selections differ from saved draft. Inspect board/device fields, then save explicitly.':'Imported selections match saved draft.');});
    window.addEventListener('sv08-authority-changed',()=>{invalidate();controls();if(!authority())notice('Administrator access ended. Pending review cancelled. Authorize and reload before editing.');else if (changed || reconcile) { reconcile=true; controls(); notice('Administrator access restored. Reconcile saved state explicitly; local selections retained.'); } else operation(()=>load());});
    window.addEventListener('sv08-navigation-changed',()=>{ if(busy && !loading) reconcile=true; invalidate(false); controls(); });
    window.addEventListener('beforeunload',event=>{if(changed){event.preventDefault();event.returnValue='';}});
    window.addEventListener('pagehide',()=>invalidate());
    window.sv08Session.ready.then(()=>{controls();if(authority())operation(load);else notice('Authorize to load private printer configuration.');});
})();
