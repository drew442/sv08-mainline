'use strict';
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
        if(context){context.replaceChildren();context.hidden=groups[parent].length===1;for(const [target,label] of groups[parent]){const button=document.createElement('button');button.dataset.page=target;button.dataset.open=target;button.textContent=label;if(target===name)button.setAttribute('aria-current','page');button.onclick=()=>window.sv08Navigation.go(target);context.append(button);}}
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
    paint(false);
})();
