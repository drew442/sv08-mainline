'use strict';
(() => {
    const $ = id => document.getElementById(id);
    const names = {password:'Password',none:'No login',certificate:'Client certificate'};
    let state = null, pending = null, busy = false, epoch = 0, refreshId = 0;
    const active = () => location.hash === '#mainsail-access' && window.sv08Session?.elevated;
    const report = message => { $('access-status').textContent = message; };
    const selected = () => document.querySelector('input[name="access-mode"]:checked')?.value;
    function clearSecrets() {
        for (const id of ['access-password','access-password-confirm','access-download-password','access-download-confirm']) $(id).value = '';
    }
    function controls() {
        document.querySelectorAll('#mainsail-access input, #mainsail-access [data-access-action]').forEach(element => {
            element.disabled = busy || !active() || !state;
        });
        $('access-refresh').disabled = busy || !active();
        const mode = selected();
        $('access-password-fields').hidden = mode !== 'password';
        $('access-none-detail').hidden = mode !== 'none';
        $('access-certificate-detail').hidden = mode !== 'certificate';
        $('access-apply').disabled ||= mode === state?.mode && (mode !== 'password' || !$('access-password').value);
    }
    function privateTransport() {
        if (location.protocol !== 'https:' && !['localhost','127.0.0.1','[::1]','::1'].includes(location.hostname)) {
            throw new Error('Use HTTPS to download a private client certificate.');
        }
    }
    async function call(request) {
        if (!active()) throw new Error('Administrator access is required.');
        if (request.method === 'certificate.create') privateTransport();
        const generation = epoch;
        const raw = await cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_mainsail_access.py'],{superuser:'require',err:'message'}).input(JSON.stringify(request));
        if (generation !== epoch || !active()) throw new Error('Access changed. Refresh before retrying.');
        const response = JSON.parse(raw);
        if (!response.ok) throw new Error(response.error || 'Mainsail access operation failed.');
        return response.result;
    }
    function renderCertificates() {
        $('access-certificates').replaceChildren();
        for (const certificate of state.certificates || []) {
            const row = document.createElement('article');
            const heading = document.createElement('h3'); heading.textContent = certificate.label;
            const dates = document.createElement('p'); dates.textContent = 'Expires: '+certificate.expires+(certificate.revoked ? ' · Revoked' : '');
            const fingerprint = document.createElement('code'); fingerprint.textContent = certificate.fingerprint;
            row.append(heading,dates,fingerprint);
            if (!certificate.revoked) {
                const button = document.createElement('button'); button.textContent = 'Revoke certificate'; button.dataset.accessAction = '';
                button.addEventListener('click',() => review('Revoke client certificate', 'Browsers using '+certificate.label+' will lose Mainsail access.',{method:'certificate.revoke',id:certificate.id}));
                row.append(document.createElement('br'),button);
            }
            $('access-certificates').append(row);
        }
    }
    async function refresh() {
        if (!active()) return;
        report('Loading Mainsail access settings…');
        const generation = epoch, attempt = ++refreshId;
        try {
            const result = await call({method:'status'});
            if (generation !== epoch || attempt !== refreshId) return;
            state = result; $('access-current').textContent = names[state.mode] || state.mode;
            document.querySelectorAll('input[name="access-mode"]').forEach(input => {input.checked = input.value === state.mode;});
            renderCertificates(); controls(); report(state.warning ? state.warning : 'Mainsail access settings are ready.');
        } catch (error) {
            if (generation !== epoch || attempt !== refreshId) return;
            state = null; controls(); report(error.message);
        }
    }
    function review(title, detail, request) {
        if (busy || !active() || !state) return;
        pending = {request,epoch}; $('access-review-title').textContent = title;
        $('access-review-detail').textContent = detail; $('access-review').returnValue = ''; $('access-review').showModal();
    }
    function matchingPassword(first, second) {
        const password = $(first).value;
        if (password.length < 8) throw new Error('Use a password with at least 8 characters.');
        if (password !== $(second).value) throw new Error('Passwords do not match.');
        return password;
    }
    $('access-refresh').addEventListener('click',() => {clearSecrets(); pending = null; $('access-review').close('cancel'); void refresh();});
    document.querySelectorAll('input[name="access-mode"]').forEach(input => input.addEventListener('change',() => {clearSecrets();controls();}));
    $('access-password').addEventListener('input',controls);
    $('access-apply').addEventListener('click',() => {
        try {
            const mode = selected(), request = {method:'settings',mode};
            if (mode === 'password') request.password = matchingPassword('access-password','access-password-confirm');
            if (mode === state.mode && mode !== 'password') return;
            review('Change Mainsail access',mode === 'none' ? 'Anyone who can reach Mainsail can control the printer. Confirm to remove login protection.' :
                mode === 'certificate' ? 'Confirm that you have imported a valid client certificate into your browser. Mainsail will require it for access.' : 'Mainsail will require the username sv08 and this password.',request);
            clearSecrets(); controls();
        } catch (error) {report(error.message);}
    });
    $('access-create').addEventListener('click',() => {
        try {
            privateTransport();
            const label = $('access-label').value.trim(); if (!label) throw new Error('Enter a certificate label.');
            const password = matchingPassword('access-download-password','access-download-confirm');
            review('Generate browser client certificate','Keep the downloaded file and password private. Import the file into your browser’s personal certificates. The current login method will remain unchanged.',{method:'certificate.create',label,password});
            clearSecrets();
        } catch (error) {report(error.message);}
    });
    $('access-review').addEventListener('close',() => {
        const action = pending; pending = null; clearSecrets();
        if ($('access-review').returnValue !== 'confirm' || !action || action.epoch !== epoch || !active() || busy) return;
        const generation = epoch;
        busy = true; controls();
        void (async () => {
            try {
                const result = await call(action.request);
                if (action.request.method === 'certificate.create') {
                    privateTransport();
                    const bytes = Uint8Array.from(atob(result.pkcs12_base64),c => c.charCodeAt(0));
                    const url = URL.createObjectURL(new Blob([bytes],{type:'application/x-pkcs12'}));
                    const link = document.createElement('a'); link.href = url; link.download = result.filename; link.click();
                    setTimeout(() => URL.revokeObjectURL(url),1000);
                }
                await refresh();
                if (generation === epoch) report(action.request.method === 'certificate.create' ? 'Certificate downloaded once. Import it into your browser, then separately apply Client certificate access.' : 'Mainsail access updated.');
            } catch (error) {if (generation === epoch) report(error.message);}
            finally {action.request.password = undefined; busy = false; controls();}
        })();
    });
    function invalidate() {
        ++epoch; ++refreshId; state = null; pending = null; clearSecrets(); $('access-label').value = '';
        $('access-review').close('cancel'); $('access-current').textContent = '—'; $('access-certificates').replaceChildren();
        controls(); report(window.sv08Session?.elevated ? 'Loading Mainsail access settings…' : 'Administrator access is required.');
    }
    window.addEventListener('sv08-authority-changed',() => {invalidate();if(active()) void refresh();});
    window.addEventListener('sv08-navigation-changed',event => {invalidate();if(event.detail.to === 'mainsail-access') void refresh();});
    controls(); if (location.hash === '#mainsail-access') void window.sv08Session.ready.then(refresh);
})();
