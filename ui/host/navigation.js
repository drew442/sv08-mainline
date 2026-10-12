'use strict';
// Presentation derives only from public read state; it never submits operations.
window.sv08Presentation = {
    visibleDevice(d) {
        if(d.device === 'lo' || d.type === 'loopback') return false;
        if(!/^p2p-dev-wlan/.test(d.device ?? '')) return true;
        // A saved UUID/name is not proof of an active P2P connection. Preserve
        // active and unknown states; hide only NM's explicitly idle devices.
        return !['disconnected','unavailable','unmanaged'].includes((d.state ?? '').toLowerCase());
    },
    update(state) {
        const phase=state.transaction?.phase;
        if(phase === 'failed') return {tone:'error',icon:'error',title:'Update failed',detail:'The update did not complete. Inspect its operation history before choosing the next step. The running release and boot selection are shown separately.'};
        if(phase === 'cancelled') return {tone:'neutral',icon:'info',title:'Update cancelled',detail:'The update was cancelled. Check the current boot selection before starting another update.'};
        if(phase === 'complete') return {tone:'success',icon:'check',title:'Update complete',detail:'The update transaction completed. The running release is shown above.'};
        if(state.pending) return {tone:'warning',icon:'clock',title:state.pending.phase === 'trial' ? 'Trial boot awaiting confirmation' : 'Update selected for next boot',detail:`Slot ${state.pending.slot} · ${state.pending.release}. ${state.pending.phase === 'trial' ? 'Boot health confirmation is still pending.' : 'Restart and boot health confirmation are still pending.'}`};
        const labels={preparing:'Preparing update',installing:'Installing update',staged:'Update staged — choose the next boot',arming:'Selecting the next boot',armed:'Update armed — check boot selection',confirming:'Confirming update health'};
        if(labels[phase]) return {tone:'warning',icon:'clock',title:labels[phase],detail:phase==='staged'?'Installation is staged. Choosing the next boot and restarting remain separate reviewed operations.':'The update is still in progress. Refresh and inspect its operation history before continuing.'};
        if(phase) return {tone:'neutral',icon:'info',title:'Update state unknown',detail:'Reported phase: '+phase+'. Refresh and inspect operation history; completion has not been established.'};
        return {tone:'neutral',icon:'info',title:'No update waiting',detail:'The running system stays active until you select a verified release for the next boot.'};
    },
    icon(name='boards') {
        const paths={boards:'M6 6h20v20H6zM11 11h10v10H11zM2 10h4m20 0h4M2 22h4m20 0h4',ethernet:'M8 3h16v12H8zM12 3v5m4-5v5m4-5v5M16 15v8M6 28h20M8 23h16v5H8z',network:'M4 12c7-8 17-8 24 0M8 17c5-5 11-5 16 0M12 22c3-3 5-3 8 0M16 27h0',overview:'M4 14L16 4l12 10M8 12v16h16V12',images:'M5 5h22v22H5zM16 9v14m-5-5 5 5 5-5',settings:'M6 8h20M6 16h20M6 24h20M12 5v6m8 2v6m-9 2v6',identity:'M16 3l11 5v8c0 6-11 13-11 13S5 22 5 16V8z',check:'M5 17l7 7L27 8',error:'M16 3a13 13 0 1 0 0 26 13 13 0 0 0 0-26M11 11l10 10m0-10L11 21',clock:'M16 3a13 13 0 1 0 0 26 13 13 0 0 0 0-26M16 8v9l6 3',info:'M16 3a13 13 0 1 0 0 26 13 13 0 0 0 0-26M16 14v9m0-14v1'};
        const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 32 32');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');svg.classList.add('outline-icon');const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',paths[name]??paths.boards);svg.append(path);return svg;
    },
    label(element,icon='boards') {
        if(!element || /^H[1-6]$/.test(element.tagName) || element.querySelector(':scope > svg')) return;
        element.prepend(this.icon(icon));
    },
    status(element,text,tone,icon) {
        element.textContent=text;element.dataset.tone=tone;element.prepend(this.icon(icon));
    }
};

(() => {
    const groups = {
        overview: [['overview','Overview']],
        printer: [['printer','Components'],['definitions','Find definitions'],['definition-sources','Definition sources'],['printer-connections','Connections']],
        images: [['images','Updates']],
        network: [['network','Network']],
        'mainsail-access': [['mainsail-access','Mainsail login'],['identity','Printer trust & identity']],
        settings: [['settings','Operating mode'],['software','Additional software'],['recovery','Recovery']]
    };
    const aliases = {hardware:'printer',updates:'images',access:'mainsail-access',system:'settings'};
    const routes = new Map(Object.entries(groups).flatMap(([parent, children])=>children.map(([route])=>[route,parent])));
    let lastActivatedControl;
    document.addEventListener('click',event=>{const control=event.target.closest?.('button,a,input');if(control)lastActivatedControl=control;},true);
    // Native dialogs keep Escape semantics; return focus to the initiating control.
    for(const dialog of document.querySelectorAll('dialog')){
        const heading=dialog.querySelector('h2');if(heading&&!dialog.hasAttribute('aria-labelledby')){heading.id ||= dialog.id+'-title';dialog.setAttribute('aria-labelledby',heading.id);}
        let trigger;
        dialog.addEventListener('beforetoggle',event=>{if(event.newState==='open')trigger=lastActivatedControl&&!dialog.contains(lastActivatedControl)?lastActivatedControl:document.activeElement;});
        dialog.addEventListener('close',()=>{setTimeout(()=>{const target=trigger?.isConnected?trigger:trigger?.dataset.definitionReference?Array.from(document.querySelectorAll('[data-definition-reference]')).find(e=>e.dataset.definitionReference===trigger.dataset.definitionReference):trigger?.id?document.getElementById(trigger.id):null;if(target&&!target.disabled&&target.getClientRects().length&&!document.querySelector('dialog[open]'))target.focus();},0);});
    }
    let current;
    const menu=document.getElementById('navigation-toggle'), nav=document.getElementById('task-navigation');
    function closeMenu(returnFocus=false){menu?.setAttribute('aria-expanded','false');nav?.classList.remove('menu-open');if(returnFocus)menu?.focus();}
    menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('menu-open',open);if(open)nav.querySelector('[aria-current="page"]')?.focus();});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu?.getAttribute('aria-expanded')==='true'){event.preventDefault();closeMenu(true);}});
    document.querySelector('.skip')?.addEventListener('click',event=>{event.preventDefault();document.getElementById('main').focus();});
    function focusPage() {const heading=document.querySelector('#'+current+' h1');if(heading){heading.tabIndex=-1;heading.focus();}else document.getElementById('main').focus();}
    function paint(focus = true) {
        const requested = location.hash.slice(1), route=aliases[requested]??requested;
        const name = routes.has(route) && document.getElementById(route) ? route : 'overview', parent=routes.get(name);
        if (requested !== name) history.replaceState(null, '', '#'+name);
        const changed=name!==current, previous=current;
        current=name;
        document.querySelectorAll('main > .page').forEach(p => { p.hidden = p.id !== name; });
        nav?.querySelectorAll('[data-page]').forEach(b => {if(b.dataset.page===parent)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
        const context=document.getElementById('task-context');
        if(context){context.replaceChildren();context.hidden=groups[parent].length===1;for(const [target,label] of groups[parent]){const button=document.createElement('button');button.dataset.page=target;button.dataset.open=target;button.textContent=label;sv08Presentation.label(button,target==='identity'||target==='mainsail-access'?'identity':target==='settings'||target==='software'||target==='recovery'?'settings':'boards');if(target===name)button.setAttribute('aria-current','page');button.onclick=()=>window.sv08Navigation.go(target);context.append(button);}}
        const hostRoutes=['overview','images','settings','recovery'];
        document.querySelectorAll('[data-host-status]').forEach(e=>{e.hidden=e.id==='image-history'?name!=='images':!hostRoutes.includes(name);});
        document.getElementById('notice').hidden=!hostRoutes.includes(name);
        document.getElementById('jobs-summary').closest('article').hidden=name!=='images';
        closeMenu();
        if(changed)window.dispatchEvent(new CustomEvent('sv08-navigation-changed',{detail:{from:previous,to:name}}));
        if (focus && changed) focusPage();
    }
    window.sv08Navigation = {get current(){return current;},go(name){name=aliases[name]??name;if(!routes.has(name))name='overview';if(location.hash!=='#'+name)history.pushState(null,'','#'+name);paint();}};
    document.querySelectorAll('[data-page],[data-open]').forEach(b=>b.addEventListener('click',()=>window.sv08Navigation.go(b.dataset.page||b.dataset.open)));
    window.addEventListener('hashchange',()=>paint());
    window.addEventListener('popstate', () => {
        paint(false);
        const destination=current;
        // Native history may restore the previous focused control after popstate.
        // Finish route focus after that restoration, without changing history.
        setTimeout(() => {
            if(current===destination&&!document.querySelector('dialog[open]'))focusPage();
        },0);
    });
    function decorateObjects(){
        for(const element of document.querySelectorAll('[data-page],[data-open],#task-navigation a,[data-printer-view],#printer-definitions-breadcrumb button,#printer-map-toggle,#printer-table-toggle')){
            const route=element.dataset.page??element.dataset.open;
            sv08Presentation.label(element,route==='network'?'network':route==='overview'?'overview':route==='images'?'images':['settings','software','recovery'].includes(route)?'settings':['identity','mainsail-access'].includes(route)?'identity':'boards');
        }
        // Object icons sit alongside plain headings, or inside non-heading labels.
        const selectors=['.metrics article','#slots article','#network-devices article','#access-certificates article','#upload-list > p','.printer-selected-definition','.printer-source-card','.printer-change','#printer-components label','#printer-boards legend','#printer-devices legend','#printer-sensors > div > p','.printer-graph-heading','#printer-connection-table tbody button'];
        for(const element of document.querySelectorAll(selectors.join(',')))sv08Presentation.label(element,element.closest('#network')?(element.dataset.type==='ethernet'?'ethernet':'network'):element.closest('#access-certificates')?'identity':'boards');
    }
    new MutationObserver(decorateObjects).observe(document.getElementById('main'),{childList:true,subtree:true});
    decorateObjects();
    paint(false);
})();
