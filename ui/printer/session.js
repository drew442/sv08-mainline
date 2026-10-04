'use strict';
// Cockpit 337's internal Superuser API, pinned with package/source provenance.
// Authentication only changes session authority; it never submits an operation.
window.sv08Session = {available: false, elevated: false};
window.sv08Session.ready = (async () => {
    const element = id => document.getElementById(id);
    const dialog = element('authorization'), password = element('authorization-password');
    let client, proxy, prompting = false, generation = 0, stopping = false, failure = '';
    const clear = () => { password.value = ''; prompting = false; element('authorization-prompt').textContent = ''; };
    const changed = () => window.dispatchEvent(new Event('sv08-authority-changed'));
    const close = () => { clear(); if (dialog.open) dialog.close(); };
    const diagnostic = message => { element('session-status').textContent = message; };
    function render() {
        const current = proxy?.Current;
        const elevated = !stopping && window.sv08Session.available && ['sudo', 'root'].includes(current);
        if (window.sv08Session.elevated !== elevated) { window.sv08Session.elevated = elevated; changed(); }
        element('authorize').disabled = stopping || !window.sv08Session.available || current !== 'none';
        element('stop-authorization').disabled = !elevated || current === 'root';
        if (failure) diagnostic(failure);
        else if (window.sv08Session.available) diagnostic(elevated ? 'Administrator access' : current === 'init' ? 'Authorizing…' : 'Limited access — authorize to administer this host.');
    }
    async function stop() {
        ++generation; stopping = true; close(); render(); changed();
        try { await proxy?.Stop(); stopping = false; render(); }
        catch (_) { failure = 'Could not stop administrator access. Log out to end this session.'; render(); }
    }
    element('logout').addEventListener('click', () => {
        ++generation; close(); window.sv08Session.available = false; window.sv08Session.elevated = false; changed();
        if (window.cockpit?.logout) cockpit.logout(true);
        else diagnostic('Session logout is unavailable. Close this window.');
    });
    dialog.addEventListener('cancel', event => { event.preventDefault(); void stop(); });
    element('cancel-authorization').addEventListener('click', () => { void stop(); });
    element('stop-authorization').addEventListener('click', () => { void stop(); });
    element('authorization-form').addEventListener('submit', async event => {
        event.preventDefault(); if (!prompting) return;
        let answer = password.value; clear(); element('answer-authorization').disabled = true;
        try { await proxy.Answer(answer); }
        catch (_) { await stop(); diagnostic('Authorization failed. Try again.'); }
        finally { answer = ''; }
    });
    element('authorize').addEventListener('click', async () => {
        if (stopping || !window.sv08Session.available || proxy.Current !== 'none') return;
        const attempt = ++generation; let failed = false; failure = ''; clear(); changed();
        try { await proxy.Start('sudo'); }
        catch (_) { failed = true; }
        finally { if (attempt === generation) { close(); render(); if (failed) { failure = 'Authorization failed or was cancelled.'; render(); } } }
    });
    try {
        if (!window.cockpit?.dbus || !cockpit.logout) throw new Error('Missing session API');
        client = cockpit.dbus(null, {bus: 'internal'});
        proxy = client.proxy('cockpit.Superuser', '/superuser');
        await Promise.race([new Promise(resolve => proxy.wait(resolve)), new Promise((_, reject) => setTimeout(() => reject(new Error('Session API timeout')), 10000))]);
        if (!proxy.valid || !Array.isArray(proxy.Bridges) || !proxy.Bridges.includes('sudo') ||
            !['none', 'init', 'sudo', 'root'].includes(proxy.Current) ||
            !['Start', 'Answer', 'Stop'].every(name => typeof proxy[name] === 'function')) throw new Error('Incompatible session API');
        window.sv08Session.available = true;
        proxy.addEventListener('changed', render);
        proxy.addEventListener('Prompt', (_event, _message, prompt, _default, echo, error) => {
            clear();
            if (echo) { void stop(); diagnostic('Unsupported authorization prompt. Access was not granted.'); return; }
            prompting = true; element('authorization-prompt').textContent = [error, prompt].filter(Boolean).join('\n');
            element('answer-authorization').disabled = false;
            if (!dialog.open) dialog.showModal(); password.focus();
        });
        client.addEventListener('close', () => {
            ++generation; close(); window.sv08Session.available = false; window.sv08Session.elevated = false;
            changed(); render(); diagnostic('Session disconnected. Log in again to reconnect.');
        });
        render(); return true;
    } catch (_) {
        close(); render(); diagnostic('Administrator access is unavailable: the required Cockpit 337 session API or sudo bridge is missing.');
        return false;
    }
})();
