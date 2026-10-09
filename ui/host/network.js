'use strict';
(() => {
    const $ = id => document.getElementById('network-'+id);
    const active = () => location.hash === '#network' && window.sv08Session?.elevated;
    let state = null, epoch = 0, refreshId = 0, busy = false, review = null, networks = [];
    const report = text => { $('status').textContent = text; };
    const clearSecrets = () => { $('password').value = ''; };
    const eraseReview = () => { if(review?.request) review.request.password = ''; review = null; };
    const split = value => value.split(',').map(x => x.trim()).filter(Boolean);
    const security = value => {
        if(['open','wpa-psk','sae'].includes(value)) return value;
        if(!value || value === '--') return 'open';
        if(/802\.1X|EAP|enterprise/i.test(value)) return 'unsupported';
        if(/WPA[12]/i.test(value)) return 'wpa-psk';
        if(/WPA3/i.test(value)) return 'sae';
        return 'unsupported';
    };
    function controls() {
        document.querySelectorAll('#network input, #network select, #network button').forEach(e => {e.disabled = busy || !active() || !state;});
        $('refresh').disabled = busy || !active();
        const wifi = state?.devices.find(d => d.device === $('device').value)?.type === 'wifi';
        $('wifi').hidden = !wifi;
        $('apply').disabled ||= wifi && !['open','wpa-psk','sae'].includes($('security').value);
        for (const id of ['apply','name','restart']) $(id).disabled ||= !!state?.pending;
        for (const id of ['confirm','rollback']) $(id).disabled ||= !state?.pending;
        $('password').disabled ||= location.protocol !== 'https:' || $('security').value === 'open';
        for(const id of ['addresses','gateway']) $(id).disabled ||= $('method').value === 'auto';
    }
    async function call(request) {
        if(!active()) throw Error('Administrator access is required.');
        if(request.password && location.protocol !== 'https:') throw Error('Use HTTPS to submit a WiFi password.');
        const generation = epoch;
        const raw = await cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_network.py'],{superuser:'require',err:'message'}).input(JSON.stringify(request));
        if(generation !== epoch || !active()) throw Error('Access changed. Reload Network.');
        const response = JSON.parse(raw);
        if(!response.ok) throw Error(response.error || 'Network operation failed.');
        return response.result;
    }
    function options(id, rows) {
        $(id).replaceChildren(...rows.map(([value,label]) => {const o = document.createElement('option');o.value=value;o.textContent=label;return o;}));
    }
    function connection() {
        clearSecrets();
        const saved = state?.connections.find(c => c.uuid === $('connection').value);
        const ip = saved?.ipv4 || {method:'auto',addresses:[],gateway:'',dns:[]};
        for(const key of ['method','gateway']) $(key).value = ip[key] || (key === 'method' ? 'auto' : '');
        for(const key of ['addresses','dns']) $(key).value = (Array.isArray(ip[key]) ? ip[key] : split(ip[key] || '')).join(', ');
        // Only public profile metadata is returned; saved secrets remain in NetworkManager.
        $('ssid').value = saved?.ssid || ''; $('security').value = saved?.security || 'wpa-psk'; controls();
    }
    function device() {
        networks = []; options('networks', [['','Scan to choose a network']]);
        options('connection',[['','Create a new connection'],...state.connections.filter(c => c.device === $('device').value || (!c.device && c.type === state.devices.find(d => d.device === $('device').value)?.type)).map(c => [c.uuid,c.name])]);
        const current = state.devices.find(d => d.device === $('device').value)?.uuid;
        if(state.connections.some(c => c.uuid === current)) $('connection').value = current;
        connection();
    }
    function links() {
        $('links').replaceChildren();
        const hosts = [state.hostname,state.fqdn,...state.devices.flatMap(d => d.addresses || []).map(a => a.split('/')[0])];
        for(const host of [...new Set(hosts.filter(Boolean))]) {
            if(!/^[a-zA-Z0-9.-]+$/.test(host) && !/^[0-9a-fA-F:]+$/.test(host)) continue;
            try {const url = new URL(location.href);url.hostname = host.includes(':') ? '['+host+']' : host;
                const link = document.createElement('a');link.href=url.href;link.textContent='Reconnect at '+host;const p=document.createElement('p');p.append(link);$('links').append(p);
            } catch (_) { /* Ignore malformed addresses; never redirect. */ }
        }
    }
    function countdown() {
        const pending = state?.pending; $('pending').hidden = !pending;
        if(!pending) return;
        const remaining = Math.max(0,Math.ceil(Number(pending.expires)-Date.now()/1000));
        $('countdown').textContent = Number.isFinite(remaining) && remaining > 0 ? 'Confirm within '+remaining+' seconds, or previous settings will be restored.' : 'Rollback deadline reached. Refresh to check restored settings.';
        if(!Number.isFinite(remaining) || remaining <= 0) { $('confirm').disabled = true; }
    }
    async function refresh() {
        if(!active()) return;
        const generation = epoch, attempt = ++refreshId;report('Loading network settings…');
        try {
            const result = await call({method:'status'});
            if(generation !== epoch || attempt !== refreshId) return;
            state=result;
            $('devices').replaceChildren(...state.devices.map(d => {const p=document.createElement('p');p.textContent=[d.device,d.state,d.connection,(d.addresses || []).join(', '),'Gateway: '+(d.gateway || '—'),'DNS: '+(d.dns || []).join(', ')].filter(Boolean).join(' · ');return p;}));
            options('device',state.devices.filter(d => ['wifi','ethernet'].includes(d.type)).map(d => [d.device,d.device+' ('+d.type+')']));device();
            $('hostname').value=state.hostname; $('fqdn').value=state.fqdn || '';links();controls();countdown();report('Network settings are ready.');
        } catch(error) {if(generation === epoch && attempt === refreshId) {if(!state?.pending) state=null;controls();countdown();report(error.message+' Reconnect and reload Network; unconfirmed changes automatically roll back.');}}
    }
    function openReview(request,title) {
        if(busy || !active() || !state) return;
        eraseReview();review={request,epoch};
        const detail = request.method === 'restart' ? 'The printer will restart and this session will disconnect.' : request.kind === 'name' ? 'Printer name: '+request.hostname+'\nFully qualified name: '+(request.fqdn || 'None') : 'Interface: '+request.device+'\nConnection: '+($('connection').selectedOptions[0]?.textContent || 'New connection')+(request.kind === 'wifi' ? '\nWiFi: '+request.ssid+'\nSecurity: '+request.security : '')+'\nIPv4: '+(request.ipv4.method === 'auto' ? 'Automatic (DHCP)' : request.ipv4.addresses.join(', '))+'\nGateway: '+(request.ipv4.gateway || 'Automatic')+'\nDNS: '+(request.ipv4.dns.join(', ') || 'Automatic')+'\nPrinter name: '+request.hostname+'\nFully qualified name: '+(request.fqdn || 'None');
        $('review-title').textContent=title;$('review-detail').textContent=detail;
        clearSecrets();$('review').returnValue='';$('review').showModal();
    }
    async function execute(request) {
        const generation=epoch;busy=true;controls();
        try {
            const result=await call(request);
            if(result?.confirm_required) {state.pending={token:result.token,expires:result.expires};controls();countdown();}
            if(request.method === 'restart') report('Restart requested. Reconnect and reload after the printer restarts.');
            else await refresh();
        } catch(error) {
            if(generation === epoch) {
                // An apply may have succeeded before transport failed. Recover its token from status.
                await refresh();
                if(generation === epoch) report(error.message+' Reconnect and reload Network. Unconfirmed changes automatically restore previous settings.');
            }
        } finally {if('password' in request) request.password='';if(generation === epoch) {busy=false;controls();countdown();}}
    }
    $('device').addEventListener('change',device);$('connection').addEventListener('change',connection);
    $('security').addEventListener('change',() => {clearSecrets();controls();});
    $('refresh').addEventListener('click',() => {clearSecrets();eraseReview();$('review').close('cancel');void refresh();});
    $('scan').addEventListener('click',async () => {
        const generation=epoch;busy=true;controls();
        try {const result=await call({method:'wifi.scan',device:$('device').value});networks=result.networks;options('networks',[['','Choose a network'],...networks.map((n,i) => [String(i),n.ssid+' · '+n.signal+'% · '+n.security])]);report('WiFi scan complete.');}
        catch(error) {if(generation === epoch) report(error.message);}
        finally {if(generation === epoch) {busy=false;controls();}}
    });
    $('networks').addEventListener('change',() => {const n=networks[Number($('networks').value)];if($('networks').value !== '' && n) {
        const saved=state.connections.find(c => c.uuid === $('connection').value);
        if(saved && saved.ssid !== n.ssid) $('connection').value='';
        $('ssid').value=n.ssid;$('security').value=security(n.security);clearSecrets();controls();
        if($('security').value !== security(n.security)) report('This network requires a security method that this page does not support.');
    }});
    $('method').addEventListener('change',controls);
    $('apply').addEventListener('click',() => {
        const kind=state.devices.find(d => d.device === $('device').value)?.type;
        if(!kind) return;
        const password=$('password').value;
        if(password && location.protocol !== 'https:') {clearSecrets();report('Use HTTPS to submit a WiFi password.');return;}
        openReview({method:'apply',kind,device:$('device').value,ssid:kind === 'wifi' ? $('ssid').value : '',security:kind === 'wifi' ? $('security').value : 'open',password:kind === 'wifi' ? password : '',connection_uuid:$('connection').value,ipv4:{method:$('method').value,addresses:$('method').value === 'manual' ? split($('addresses').value) : [],gateway:$('method').value === 'manual' ? $('gateway').value.trim() : '',dns:split($('dns').value)},hostname:$('hostname').value.trim(),fqdn:$('fqdn').value.trim()},'Change network connection');
    });
    $('name').addEventListener('click',() => openReview({method:'apply',kind:'name',hostname:$('hostname').value.trim(),fqdn:$('fqdn').value.trim()},'Change printer name'));
    $('restart').addEventListener('click',() => openReview({method:'restart',confirm:true},'Restart printer'));
    for(const method of ['confirm','rollback']) $(method).addEventListener('click',() => {if(state?.pending) void execute({method,token:state.pending.token});});
    $('review').addEventListener('close',() => {
        const action=review;review=null;clearSecrets();
        if($('review').returnValue === 'confirm' && action?.epoch === epoch && active() && !busy) void execute(action.request);
        else if(action) action.request.password='';
    });
    function invalidate() {
        ++epoch;++refreshId;busy=false;state=null;eraseReview();clearSecrets();$('review').close('cancel');$('devices').replaceChildren();$('links').replaceChildren();$('pending').hidden=true;controls();report(window.sv08Session?.elevated ? 'Loading network settings…' : 'Administrator access is required.');
    }
    window.addEventListener('sv08-authority-changed',() => {invalidate();if(active()) void refresh();});
    window.addEventListener('sv08-navigation-changed',event => {invalidate();if(event.detail.to === 'network') void refresh();});
    setInterval(countdown,1000);controls();if(location.hash === '#network') void window.sv08Session.ready.then(refresh);
})();
