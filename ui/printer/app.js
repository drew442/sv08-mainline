'use strict';
(() => {
    const $ = id => document.getElementById(id);
    let catalog, draft, revision, saved, review, busy = false, epoch = 0, changed = false;
    const copy = value => JSON.parse(JSON.stringify(value));
    const notice = text => { $('notice').textContent = text; };
    const invalidate = () => { review = null; ++epoch; if ($('candidate-review').open) $('candidate-review').close(); };
    const edit = () => { changed = true; invalidate(); notice('Unsaved selections. Save draft before reviewing.'); };
    const authority = () => window.sv08Session?.available && window.sv08Session.elevated;
    function controls() {
        for (const id of ['save','review','restore','add','apply','import']) $(id).disabled = busy || !authority() || (!draft && id !== 'import');
        $('review').disabled ||= changed || !draft;
        $('apply').disabled ||= !review?.complete;
        $('restore').disabled ||= !saved?.previous;
    }
    async function rpc(request) {
        if (!authority()) throw new Error('Administrator access is required.');
        const attempt = epoch;
        const proc = cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_printer_helper.py'], {superuser:'require',err:'message'});
        proc.input(JSON.stringify(request));
        const raw = await proc;
        if (!authority() || attempt !== epoch) throw new Error('Session or selections changed. Reload saved configuration.');
        const reply = JSON.parse(raw);
        if (!reply.ok) throw new Error(reply.error);
        return reply.result;
    }
    async function operation(fn) {
        if (busy) return; busy = true; controls();
        try { await fn(); }
        catch (e) { invalidate(); notice(e.message + ' If a save was not acknowledged, reload to reconcile before retrying.'); }
        finally { busy = false; controls(); }
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
        else {control=el('input');control.type=type==='text'?'text':'number';if(control.type==='number')control.step='any';control.value=value??'';control.addEventListener('change',()=>onchange(control.value===''?undefined:control.type==='number'?Number(control.value):control.value));}
        return label(text,control);
    }
    function boardData(role) {return catalog.boards.find(b=>b.id===draft.boards[role]?.id);}
    function renderBoards() {
        $('boards').replaceChildren();
        for(const role of ['main','tool']) {
            const box=el('fieldset');box.append(el('legend',role==='main'?'Mainboard':'Toolhead board'));
            const board=boardData(role), selection=draft.boards[role]??{};
            const choice=select([['','Choose board reference'],...catalog.boards.filter(b=>b.role===role).map(b=>[b.id,b.label])],selection.id, value=>{
                if(value===selection.id)return;
                $('board-change').showModal();
                $('confirm-board').onclick=()=>{
                    invalidate();draft.boards[role]=value?{id:value}:{};
                    if(!value)delete draft.boards[role];
                    draft.devices=draft.devices.filter(d=>d.board!==role);edit();$('board-change').close();render();
                };
                $('cancel-board').onclick=()=>{$('board-change').close();renderBoards();};
                $('board-change').oncancel=()=>{renderBoards();};
                choice.value=selection.id??'';
            });
            box.append(label('Board / revision',choice));
            if(board){
                box.append(el('p',board.warning),el('small','Documented reference. Installed match: unknown. '+board.unknowns.join('; ')));
                box.append(el('small',board.source.path+' @ '+board.source.revision+'; accessed '+board.source.accessed));
                box.append(field('Transport','text',selection.transport,v=>{if(v)selection.transport=v;else delete selection.transport;delete selection.identity;edit();renderBoards();},[['serial','USB / serial'],['can','CAN']]));
                box.append(field('Private MCU identity','text',selection.identity,v=>{if(v)selection.identity=v;else delete selection.identity;edit();}));
                box.append(field('Use this reference provisionally','boolean',selection.reference_ack,v=>{if(v===undefined)delete selection.reference_ack;else selection.reference_ack=v;edit();}));
            }
            $('boards').append(box);
        }
    }
    function renderDevices() {
        $('devices').replaceChildren();
        for(const device of draft.devices) {
            const box=el('fieldset');box.append(el('legend',device.name+' · '+device.kind+' · '+device.board));
            const remove=el('button','Remove device');remove.onclick=()=>{draft.devices=draft.devices.filter(d=>d!==device);edit();renderDevices();};box.append(remove);
            const board=boardData(device.board), settings=el('div');settings.className='settings';
            if(!board){box.append(el('p','Choose a board first'));$('devices').append(box);continue;}
            for(const [name,type] of Object.entries(catalog.kinds[device.kind])) {
                let options;
                if(['adc','input','probe','heater','fan'].includes(type)) {
                    options=Object.entries(board.signals).filter(([,s])=>s.capabilities.includes(type)&&!s.reserved).map(([p])=>{
                        const c=Object.values(board.connectors).find(c=>c.pin===p&&c.capability===type);
                        return [p,(c?.label??'Reference signal')+' → '+(device.board==='tool'?'tool:':'')+p+(c?.contact?' ('+c.contact+')':' (contact unknown)')];
                    });
                } else if(type==='motor') options=Object.entries(board.motors).map(([n,p])=>[n,n+' → '+Object.entries(p).map(([k,p])=>k+':'+p).join(', ')]);
                else if(type==='curve')options=catalog.curves.map(c=>[c.id,c.label]);
                else if(type==='name')options=draft.devices.filter(d=>d.kind==='sensor'&&d.board===device.board).map(d=>[d.name,d.name]);
                else if(type==='control')options=[['pid','PID (enter gains)'],['watermark','Watermark']];
                const text=({'invert':'Invert signal','invert_dir':'Invert direction','invert_enable':'Invert enable','digital_pullup':'Digital input pull-up','pullup_resistor':'Analog pull-up resistance (ohm)','current_rating_rms':'Motor RMS rating (A), owner entered','run_current':'Driver RMS current (A)','sense_resistor':'Sense resistor (ohm), explicit','pin':'Connection / pin'}[name]??name.replaceAll('_',' '));
                settings.append(field(text,type==='name'?'text':type,device.settings[name],value=>{
                    if(value===undefined||value==='')delete device.settings[name];else device.settings[name]=value;
                    if(name==='curve'){delete device.settings.pullup_resistor;delete device.settings.min_temp;delete device.settings.max_temp;}
                    edit();if(name==='curve')renderDevices();
                },options));
            }
            box.append(settings);
            if(device.kind==='sensor') {
                const curve=catalog.curves.find(c=>c.id===device.settings.curve);
                if(curve){
                    box.append(el('small',curve.origin+'. '+curve.pullup_origin+'. Physical sensor/circuit identity unknown.'));
                    const preset=el('button','Use documented reference pull-up');
                    preset.onclick=()=>{device.settings.pullup_resistor=curve.reference_pullup;edit();renderDevices();};box.append(preset);
                }
            }
            $('devices').append(box);
        }
    }
    function render() {
        renderBoards();renderDevices();$('geometry-fields').replaceChildren();
        for(const key of ['max_velocity','max_accel','max_z_velocity','max_z_accel'])$('geometry-fields').append(field(key.replaceAll('_',' '),'positive',draft.geometry[key],v=>{if(v===undefined)delete draft.geometry[key];else draft.geometry[key]=v;edit();}));
        $('current').textContent=saved.current?'Candidate saved — inactive ('+saved.current.mode+'). Commissioning and activation require separate reviewed steps.':'No saved candidate.';
        controls();
    }
    async function load() {
        invalidate();const result=await rpc({action:'status'});catalog=result.catalog;saved=result.state;revision=saved.revision;draft=copy(saved.draft);changed=false;
        if(saved.format_version!==1){notice('Unsupported stored schema. Export for diagnosis; editing is disabled.');draft=null;return;}
        $('device-kind').replaceChildren();for(const kind of Object.keys(catalog.kinds)){const o=el('option',kind);o.value=kind;$('device-kind').append(o);}
        render();notice('Saved configuration loaded. Candidates remain inactive.');
    }
    $('reload').onclick=()=>operation(load);
    $('add').onclick=()=>{const role=$('device-board').value,name=$('device-name').value;if(!boardData(role)){notice('Choose a board reference first.');return;}if(!/^[a-z][a-z0-9_]{0,39}$/.test(name)||draft.devices.some(d=>d.name===name)){notice('Use a unique lowercase device name.');return;}draft.devices.push({name,board:role,kind:$('device-kind').value,settings:{}});edit();renderDevices();};
    $('save').onclick=()=>operation(async()=>{const result=await rpc({action:'save',expected_revision:revision,draft});revision=result.revision;changed=false;invalidate();await load();notice(result.message);});
    $('mode').onchange=()=>{invalidate();controls();};
    $('review').onclick=()=>operation(async()=>{review=await rpc({action:'review',mode:$('mode').value});$('review-detail').textContent=[...review.blockers,...review.warnings].join('\n');$('review-text').textContent=review.text??'';$('candidate-review').showModal();$('cancel-review').focus();});
    $('cancel-review').onclick=()=>{invalidate();controls();};$('candidate-review').oncancel=()=>{invalidate();controls();};
    $('apply').onclick=()=>operation(async()=>{const result=await rpc({action:'apply',mode:$('mode').value,review:review.review});invalidate();await load();notice(result.message+' — use the commissioning handoff before activation.');});
    $('restore').onclick=()=>operation(async()=>{await rpc({action:'restore',expected_revision:revision});await load();notice('Previous candidate draft restored. Review before applying.');});
    function download(name,text,type) {const url=URL.createObjectURL(new Blob([text],{type}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    $('export').onclick=()=>download('printer-hardware-draft.json',JSON.stringify(draft??saved,null,2),'application/json');
    $('export-config').onclick=()=>{if(saved?.current)download('inactive-candidate.cfg',saved.current.text,'text/plain');else notice('No saved candidate to export.');};
    $('import').onchange=()=>operation(async()=>{invalidate();const file=$('import').files[0];if(!file)return;if(file.size>131072)throw new Error('Import exceeds 128 KiB.');const incoming=JSON.parse(await file.text());const result=await rpc({action:'import',draft:incoming});draft=result.draft;revision=result.expected_revision;changed=true;render();notice(result.changed?'Imported selections differ from saved draft. Inspect board/device fields, then save explicitly.':'Imported selections match saved draft.');$('import').value='';});
    window.addEventListener('sv08-authority-changed',()=>{invalidate();controls();if(!authority())notice('Administrator access ended. Pending review cancelled. Authorize and reload before editing.');else operation(load);});
    window.addEventListener('pagehide',invalidate);
    window.sv08Session.ready.then(()=>{controls();if(authority())operation(load);else notice('Authorize to load private printer configuration.');});
})();
