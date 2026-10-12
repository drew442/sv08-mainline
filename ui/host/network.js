'use strict';
(() => {
    const $ = id => document.getElementById('network-'+id);
    const active = () => location.hash === '#network' && window.sv08Session?.available;
    let state = null, epoch = 0, refreshId = 0, busy = false, review = null, networks = [], draftValues=null, observedPending=null, refreshing=false, targetUnavailable=false, outcomeUnknown=false, readFailed=false, scanMessage='Scan for nearby networks, or enter a network name manually.';
    const draftFields=['device','connection','ssid','security','method','addresses','gateway','dns','hostname','fqdn'];
    function captureDraft(){draftValues=Object.fromEntries(draftFields.map(id=>[id,$(id).value]));}
    for(const id of draftFields)$(id).addEventListener('input',captureDraft);
    function restoreDraft(){
        if(!draftValues)return;
        const retained={...draftValues};targetUnavailable=false;
        if(!Array.from($('device').options).some(o=>o.value===retained.device)){const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Previous interface unavailable — choose an interface';$('device').prepend(placeholder);$('device').value='';targetUnavailable=true;controls();return;}
        if(Array.from($('device').options).some(o=>o.value===retained.device)){$('device').value=retained.device;device();}
        if(Array.from($('connection').options).some(o=>o.value===retained.connection)){$('connection').value=retained.connection;connection();}
        if(!Array.from($('connection').options).some(o=>o.value===retained.connection)){const placeholder=document.createElement('option');placeholder.value='unavailable';placeholder.textContent='Previous connection unavailable — choose a connection';$('connection').prepend(placeholder);$('connection').value='unavailable';targetUnavailable=true;controls();return;}
        for(const id of draftFields.filter(id=>!['device','connection'].includes(id))){const control=$(id);if(control.tagName==='SELECT'&&!Array.from(control.options).some(o=>o.value===retained[id]))continue;control.value=retained[id];}
        controls();
    }

    const report = text => { $('status').textContent = text; };
    const clearSecrets = () => { $('password').value = ''; };
    const eraseReview = () => { if(review?.request) review.request.password = ''; review = null; };
    const deviceLabel = d => (d?.type === 'wifi' ? 'WiFi' : d?.type === 'ethernet' ? 'Ethernet' : 'Network')+' ('+(d?.device || 'unavailable')+')';
    const securityLabel = value => ({open:'Open network', 'wpa-psk':'WPA personal',sae:'WPA3 personal',unsupported:'Unsupported security'}[value] || 'Unsupported security');
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
        document.querySelectorAll('#network input, #network select, #network button').forEach(e => {e.disabled = busy || !active() || !window.sv08Session?.elevated || !state;});
        $('device').disabled = busy || !active() || !state;
        $('connection').disabled = busy || !active() || !state;
        $('refresh').disabled = busy || !active();
        const selected = state?.devices.find(d => d.device === $('device').value);
        const wifi = selected?.type === 'wifi';
        $('selection').textContent = readFailed || !state ? 'Current connection status is unavailable. Reconnect and refresh before reviewing changes.' : selected ? 'Selected: '+deviceLabel(selected)+' — '+(selected.state || 'State unavailable')+(selected.connection ? ' · '+selected.connection : '') : 'No supported connection is available. Connect an Ethernet cable or check that a WiFi adapter is available, then refresh.';
        $('access-help').hidden = !!window.sv08Session?.elevated;
        $('wifi-help').textContent = $('security').value === 'unsupported' ? 'This network uses unsupported security. Choose an open, WPA personal or WPA3 personal network.' : scanMessage;
        $('password-help').textContent = $('security').value === 'open' ? 'This is an open network. It does not require a password.' : (location.protocol !== 'https:' ? 'Open this page over HTTPS to enter a WiFi password. ' : '')+($('connection').value ? 'Leave empty to reuse the saved password, if this connection has one. Saved passwords are never shown.' : 'A new secured WiFi connection requires a password.');
        $('wifi').hidden = !wifi;
        $('apply').disabled ||= targetUnavailable || !state?.devices.some(d=>d.device===$('device').value);
        $('scan').disabled ||= targetUnavailable || !wifi;
        $('apply').disabled ||= wifi && !['open','wpa-psk','sae'].includes($('security').value);
        for (const id of ['apply','name','restart']) $(id).disabled ||= !!state?.pending;
        for (const id of ['confirm','rollback']) $(id).disabled ||= !state?.pending;
        $('password').disabled ||= location.protocol !== 'https:' || $('security').value === 'open';
        for(const id of ['addresses','gateway']) $(id).disabled ||= $('method').value === 'auto';
    }
    async function call(request) {
        if(request.method === 'status') return sv08View('network');
        if(!active() || !window.sv08Session?.elevated) throw Error('Administrator access is required.');
        if(request.password && location.protocol !== 'https:') throw Error('Use HTTPS to submit a WiFi password.');
        const generation = epoch;
        const raw = await cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_network.py'],{superuser:'require',err:'message'}).input(JSON.stringify(request));
        if(generation !== epoch || !active()) throw Error('Access changed. Reload Network.');
        const response = JSON.parse(raw);
        if(!response.ok) throw Error(response.error || 'Network operation failed.');
        return response.result;
    }
    function options(id, rows) {
        const select=$(id), existing=new Map(Array.from(select.options).map(o=>[o.value,o]));
        const nodes=rows.map(([value,label])=>{const o=existing.get(value)||document.createElement('option');o.value=value;if(o.textContent!==label)o.textContent=label;return o;});
        for(const o of Array.from(select.options))if(!nodes.includes(o))o.remove();
        nodes.forEach((o,i)=>{if(select.options[i]!==o)select.insertBefore(o,select.options[i]||null);});
    }
    function connection() {
        targetUnavailable=false;clearSecrets();
        const saved = state?.connections.find(c => c.uuid === $('connection').value);
        const ip = saved?.ipv4 || {method:'auto',addresses:[],gateway:'',dns:[]};
        for(const key of ['method','gateway']) $(key).value = ip[key] || (key === 'method' ? 'auto' : '');
        for(const key of ['addresses','dns']) $(key).value = (Array.isArray(ip[key]) ? ip[key] : split(ip[key] || '')).join(', ');
        // Only public profile metadata is returned; saved secrets remain in NetworkManager.
        $('ssid').value = saved?.ssid || ''; $('security').value = saved?.security || 'wpa-psk'; controls();
    }
    function device() {
        targetUnavailable=false;networks = [];scanMessage='Scan for nearby networks, or enter a network name manually.'; options('networks', [['','Scan to choose a network']]);
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
        const pending = state?.pending || observedPending; $('pending').hidden = !pending && !outcomeUnknown;
        $('pending-title').textContent = pending ? 'Keep these network changes?' : 'Connection result is unknown';
        if(outcomeUnknown && !pending) $('countdown').textContent='The request may have reached the printer. Reconnect and refresh to check whether confirmation is needed.';
        const indicator=document.getElementById('network-operation-indicator');
        if(indicator){indicator.hidden=!pending && !outcomeUnknown;indicator.textContent=pending?'Network change awaiting confirmation — reconnect or review rollback':'Network change result unknown — reconnect and check Network';}

        if(!pending) return;
        const remaining = Math.max(0,Math.ceil(Number(pending.expires)-Date.now()/1000));
        $('countdown').textContent = Number.isFinite(remaining) && remaining > 0 ? 'Confirm within '+remaining+' seconds, or previous settings will be restored.' : 'Rollback deadline reached. Refresh to check restored settings.';
        if(!Number.isFinite(remaining) || remaining <= 0) { $('confirm').disabled = true;if(indicator)indicator.textContent='Network rollback deadline reached — check current connections'; }
    }
    async function refresh() {
        if(!active()) return;
        refreshing=true;
        const generation = epoch, attempt = ++refreshId;report('Loading network settings…');
        try {
            const result = await call({method:'status'});
            if(generation !== epoch || attempt !== refreshId) return;
            state={...result,devices:result.devices.filter(sv08Presentation.visibleDevice)};observedPending=result.pending??null;outcomeUnknown=false;readFailed=false;$('connections-title').textContent='Current connections';
            const cards=new Map(Array.from($('devices').children).map(card=>[card.dataset.device,card]));
            const currentCards=state.devices.map(d => {
                const card=cards.get(d.device)||document.createElement('article');card.className='network-connection';card.dataset.device=d.device;card.dataset.type=d.type;
                if(card.children.length){card.querySelector('h3').textContent=d.type==='wifi'?'WiFi':d.type==='ethernet'?'Ethernet':'Network';card.querySelector('strong').textContent=(d.state || 'State unavailable')+(d.connection?' · '+d.connection:'');card.querySelector('.network-address').textContent='Printer address: '+((d.addresses || []).map(a=>a.split('/')[0]).join(', ') || 'No address assigned');card.querySelector('details p').textContent='Interface: '+d.device+' · Addresses: '+((d.addresses || []).join(', ') || 'None')+' · Router: '+(d.gateway || 'None')+' · Name servers: '+((d.dns || []).join(', ') || 'None');return card;}
                const title=document.createElement('h3');title.textContent=d.type==='wifi'?'WiFi':d.type==='ethernet'?'Ethernet':'Network';card.append(title);
                const status=document.createElement('p');const strong=document.createElement('strong');strong.textContent=(d.state || 'State unavailable')+(d.connection?' · '+d.connection:'');status.append(strong);card.append(status);
                const address=document.createElement('p');address.className='network-address';address.textContent='Printer address: '+((d.addresses || []).map(a=>a.split('/')[0]).join(', ') || 'No address assigned');card.append(address);
                const details=document.createElement('details'),summary=document.createElement('summary'),technical=document.createElement('p');summary.textContent='Connection details';technical.textContent='Interface: '+d.device+' · Addresses: '+((d.addresses || []).join(', ') || 'None')+' · Router: '+(d.gateway || 'None')+' · Name servers: '+((d.dns || []).join(', ') || 'None');details.append(summary,technical);card.append(details);return card;
            });
            for(const card of Array.from($('devices').children))if(!currentCards.includes(card))card.remove();
            currentCards.forEach(card=>{const connected=/^connected/.test(state.devices.find(d=>d.device===card.dataset.device)?.state??'');sv08Presentation.status(card.querySelector('strong'),card.querySelector('strong').textContent,connected?'success':'neutral',connected?'check':'info');});
            currentCards.forEach((card,i)=>{if($('devices').children[i]!==card)$('devices').insertBefore(card,$('devices').children[i]||null);});
            if(!state.devices.length){const p=document.createElement('p');p.textContent='No network connections were reported. Check the cable or WiFi adapter, then refresh.';$('devices').append(p);}
            const previous=$('device').value;
            options('device',state.devices.filter(d => ['wifi','ethernet'].includes(d.type)).map(d => [d.device,deviceLabel(d)]));
            $('device').value=state.devices.some(d=>d.device===previous)?previous:(state.devices.find(d=>['wifi','ethernet'].includes(d.type)&&d.state==='connected')?.device || $('device').options[0]?.value || '');device();
            $('hostname').value=state.hostname; $('fqdn').value=state.fqdn || '';restoreDraft();links();controls();countdown();report(targetUnavailable ? 'Previous network target is unavailable. Choose an interface and connection before reviewing changes.' : 'Network settings are ready.');
        } catch(error) {if(generation === epoch && attempt === refreshId) {readFailed=true;$('connections-title').textContent=$('devices').children.length?'Last reported connections — refresh required':'Connection status unavailable';if(!state?.pending) state=null;controls();countdown();report(error.message+' Reconnect and reload Network; unconfirmed changes automatically roll back.');}} finally{refreshing=false;}
    }
    function openReview(request,title,trigger) {
        if(busy || !active() || !window.sv08Session?.elevated || !state) return;
        eraseReview();review={request,epoch,trigger};
        const rows=request.method==='restart'?[['Action','Restart the printer']]:request.kind==='name'?[['Printer name',request.hostname],['Full network name',request.fqdn || 'None']]:[
            ['Connection type',deviceLabel(state.devices.find(d=>d.device===request.device))],['Saved connection',$('connection').selectedOptions[0]?.textContent || 'Create a new connection'],
            ...(request.kind==='wifi'?[['WiFi network',request.ssid],['Security',securityLabel(request.security)]]:[]),
            ['Printer addresses',request.ipv4.method==='auto'?'Automatic (DHCP)':request.ipv4.addresses.join(', ')],['Router address',request.ipv4.gateway || 'Automatic'],['Name servers',request.ipv4.dns.join(', ') || 'Automatic'],['Printer name',request.hostname],['Full network name',request.fqdn || 'None']];
        $('review-title').textContent=title;
        $('review-detail').replaceChildren(...rows.flatMap(([label,value])=>{const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;return [dt,dd];}));
        $('review-consequence').textContent=request.method==='restart'?'The printer must be idle. Restart disconnects this session. Reconnect and reload after it restarts.':'These changes may disconnect this session. Reconnect and reload Network, then keep the changes before the deadline shown after applying. Without confirmation, previous settings are restored automatically.';
        $('review-cancel').textContent='Cancel keeps the settings on the printer unchanged.'+(request.kind==='wifi'?' Any WiFi password entered for this review will be cleared.':'');
        clearSecrets();$('review').returnValue='';$('review').showModal();$('review-title').focus();$('review').scrollTop=0;
    }
    async function execute(request) {
        const generation=epoch;busy=true;controls();
        try {
            const result=await call(request);draftValues=null;
            if(result?.confirm_required) {state.pending={token:result.token,expires:result.expires};observedPending=state.pending;controls();countdown();}
            if(request.method === 'restart') report('Restart requested. Reconnect and reload after the printer restarts.');
            else await refresh();
        } catch(error) {
            if(generation === epoch) {
                if(request.method==='apply')outcomeUnknown=true;
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
        try {const result=await call({method:'wifi.scan',device:$('device').value});networks=result.networks;scanMessage=networks.length?'Choose a nearby network, or enter a network name manually.':'No nearby networks were found. Scan again, move closer to the router, or enter the network name manually.';options('networks',[['','Choose a network'],...networks.map((n,i) => [String(i),(n.ssid || 'Hidden network — enter name manually')+' · '+n.signal+'% · '+securityLabel(security(n.security))])]);report('WiFi scan complete.');}
        catch(error) {if(generation === epoch) report(error.message);}
        finally {if(generation === epoch) {busy=false;controls();}}
    });
    $('networks').addEventListener('change',() => {const n=networks[Number($('networks').value)];if($('networks').value !== '' && n) {
        const saved=state.connections.find(c => c.uuid === $('connection').value);
        if(saved && saved.ssid !== n.ssid) $('connection').value='';
        $('ssid').value=n.ssid;$('security').value=security(n.security);clearSecrets();controls();captureDraft();
        if($('security').value === 'unsupported') report('This network requires a security method that this page does not support.');
    }});
    $('method').addEventListener('change',controls);
    $('apply').addEventListener('click',() => {
        const kind=state.devices.find(d => d.device === $('device').value)?.type;
        if(!kind) return;
        const password=$('password').value;
        if(password && location.protocol !== 'https:') {clearSecrets();report('Use HTTPS to submit a WiFi password.');return;}
        openReview({method:'apply',kind,device:$('device').value,ssid:kind === 'wifi' ? $('ssid').value : '',security:kind === 'wifi' ? $('security').value : 'open',password:kind === 'wifi' ? password : '',connection_uuid:$('connection').value,ipv4:{method:$('method').value,addresses:$('method').value === 'manual' ? split($('addresses').value) : [],gateway:$('method').value === 'manual' ? $('gateway').value.trim() : '',dns:split($('dns').value)},hostname:$('hostname').value.trim(),fqdn:$('fqdn').value.trim()},'Change network connection',$('apply'));
    });
    $('name').addEventListener('click',() => openReview({method:'apply',kind:'name',hostname:$('hostname').value.trim(),fqdn:$('fqdn').value.trim()},'Change printer name',$('name')));
    $('restart').addEventListener('click',() => openReview({method:'restart',confirm:true},'Restart printer',$('restart')));
    for(const method of ['confirm','rollback']) $(method).addEventListener('click',() => {if(state?.pending) void execute({method,token:state.pending.token});});
    $('review').addEventListener('close',() => {
        const action=review;review=null;clearSecrets();
        if($('review').returnValue === 'confirm' && action?.epoch === epoch && active() && !busy) void execute(action.request);
        else if(action) {action.request.password='';if(action.epoch===epoch && active()){report('Review canceled. Printer settings are unchanged; any entered WiFi password was cleared.');action.trigger?.focus();}}
    });
    function invalidate() {
        ++epoch;++refreshId;busy=false;state=null;eraseReview();clearSecrets();$('review').close('cancel');$('devices').replaceChildren();$('links').replaceChildren();$('pending').hidden=true;controls();report(window.sv08Session?.available ? 'Loading network settings…' : 'Administrator access is required.');
    }
    window.addEventListener('sv08-authority-changed',() => {invalidate();if(active()) void refresh();});
    window.addEventListener('sv08-navigation-changed',event => {invalidate();if(event.detail.to === 'network') void refresh();});
    for(const id of draftFields)$(id).addEventListener('change',captureDraft);setInterval(countdown,1000);setInterval(()=>{if(active()&&state?.pending&&!busy&&!refreshing&&!document.hidden)void refresh();},3000);controls();if(location.hash === '#network') void window.sv08Session.ready.then(refresh);
})();
