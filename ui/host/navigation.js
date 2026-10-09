'use strict';
(() => {
    const routes = new Set(['network','mainsail-access','identity','overview','images','software','settings','recovery','printer','definition-sources','printer-connections','definitions']);
    let current;
    document.querySelector('.skip')?.addEventListener('click',event=>{event.preventDefault();document.getElementById('main').focus();});
    function paint(focus = true) {
        const route = location.hash.slice(1);
        const name = routes.has(route) && document.getElementById(route) ? route : 'overview';
        if (route !== name) history.replaceState(null, '', '#'+name);
        if (name !== current) window.dispatchEvent(new CustomEvent('sv08-navigation-changed', {detail:{from:current,to:name}}));
        current = name;
        document.querySelectorAll('main > .page').forEach(p => { p.hidden = p.id !== name; });
        document.querySelectorAll('[data-page]').forEach(b => { if(b.dataset.page===name)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current'); });
        document.querySelectorAll('[data-host-status]').forEach(e => {e.hidden = ['software','network','mainsail-access','identity','printer','definition-sources','printer-connections','definitions'].includes(name);});
        document.getElementById('notice').hidden = ['software','network','mainsail-access'].includes(name);
        document.getElementById('jobs-summary').closest('article').hidden = ['software','network','mainsail-access'].includes(name);
        if (focus) document.getElementById('main').focus();
    }
    window.sv08Navigation = {go(name) {if(!routes.has(name))name='overview';if(location.hash !== '#'+name)history.pushState(null,'','#'+name);paint();}};
    document.querySelectorAll('[data-page],[data-open]').forEach(b => b.addEventListener('click',()=>sv08Navigation.go(b.dataset.page || b.dataset.open)));
    window.addEventListener('hashchange',()=>paint());
    window.addEventListener('popstate',()=>paint());
    paint(false);
})();
