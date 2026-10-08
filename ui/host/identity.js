'use strict';
(() => {
    const $ = id => document.getElementById(id);
    // Cockpit blocks parsed inline style attributes. Trusted CSSOM properties
    // keep public fingerprints and the editor usable on narrow displays.
    for (const id of ['identity-ca-fingerprint','identity-ssh-fingerprint']) {
        Object.assign($(id).style,{overflowWrap:'anywhere',whiteSpace:'normal',wordBreak:'break-all'});
    }
    Object.assign($('identity-keys').style,{width:'100%',maxWidth:'100%',minHeight:'8rem',boxSizing:'border-box'});
    Object.assign($('identity-review-detail').style,{whiteSpace:'pre-wrap',overflowWrap:'anywhere'});
    let state, pending, busy = false, epoch = 0;
    const report = text => { $('identity-status').textContent = text; };
    function controls() {
        document.querySelectorAll('[data-identity-action]').forEach(button => {
            button.disabled = busy || !window.sv08Session?.elevated || !state || (state.healthy === false && button.id !== 'identity-import');
        });
    }
    async function call(request) {
        if (!window.sv08Session?.elevated) throw new Error('Administrator access is required.');
        if (request.method === 'bundle.export' && location.protocol !== 'https:' && !['localhost','127.0.0.1','::1'].includes(location.hostname)) throw new Error('Use HTTPS to download a private identity backup.');
        const generation = epoch;
        const raw = await cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_identity.py'], {superuser:'require',err:'message'}).input(JSON.stringify(request));
        if (generation !== epoch || !window.sv08Session?.elevated) throw new Error('Administrator access ended. Reload before retrying.');
        const response = JSON.parse(raw);
        if (!response.ok) throw new Error(response.error || 'Identity operation failed.');
        return response.result;
    }
    async function refresh() {
        if (!window.sv08Session?.elevated) { state = null; controls(); return; }
        try {
            state = await call({method:'status'});
            $('identity-ca-fingerprint').textContent = state.ca_fingerprint;
            $('identity-ssh-fingerprint').textContent = state.ssh_fingerprint;
            $('identity-keys').value = state.authorized_keys;
            controls(); report(state.healthy === false ? 'Printer identity is damaged. Restore a verified identity backup.' : 'Printer identity is ready.');
        } catch (error) { state = null; controls(); report(error.message); }
    }
    function download(name, bytes, type) {
        const url = URL.createObjectURL(new Blob([bytes],{type}));
        const link = document.createElement('a'); link.href = url; link.download = name;
        link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
    }
    function base64(bytes) {
        let raw = ''; for (let offset=0;offset<bytes.length;offset+=8192) raw += String.fromCharCode(...bytes.subarray(offset,offset+8192));
        return btoa(raw);
    }
    function review(title, detail, request) {
        pending = request; $('identity-review-title').textContent = title;
        $('identity-review-detail').textContent = detail; $('identity-review').showModal();
    }
    async function operation(callback) {
        if (busy || !state || !window.sv08Session?.elevated) return;
        busy = true; controls();
        try { await callback(); }
        catch (error) { report(error.message); }
        finally { busy = false; controls(); }
    }
    $('identity-refresh').addEventListener('click',() => { void refresh(); });
    $('identity-download-ca').addEventListener('click',() => { void operation(async () => {
        const result = await call({method:'ca.download'}); download(result.filename,result.content,'application/x-x509-ca-cert');
        report('CA certificate downloaded. Import it into your trusted certificate authorities.');
    }); });
    $('identity-export').addEventListener('click',() => review('Download printer identity backup',
        'This backup contains the private CA and SSH host keys, plus trusted user public keys. Keep it private. It does not contain account passwords, network settings or printer calibration.',{method:'bundle.export'}));
    $('identity-save-keys').addEventListener('click',() => review('Replace trusted SSH user keys',
        'The displayed public keys will replace the trusted keys for sv08. Keep a key whose private key you possess. Existing SSH sessions remain open.',{method:'keys.replace',keys:$('identity-keys').value,revision:state.revision}));
    $('identity-key-file').addEventListener('change',() => { void operation(async () => {
        const file = $('identity-key-file').files[0]; if (!file) return;
        if (file.size>65536) throw new Error('SSH public-key upload is limited to 64 KiB.');
        const text = await file.text(); $('identity-keys').value = $('identity-keys').value.trimEnd()+'\n'+text;
        $('identity-key-file').value = ''; report('Public keys added to the editor. Review and save to trust them.');
    }); });
    $('identity-import').addEventListener('click',() => { void operation(async () => {
        const file = $('identity-bundle-file').files[0]; if (!file) throw new Error('Choose an identity backup.');
        if (file.size>1024*1024) throw new Error('Identity backup is limited to 1 MiB.');
        const bundle = base64(new Uint8Array(await file.arrayBuffer()));
        const result = await call({method:'bundle.preview',bundle});
        review('Restore printer identity', 'CA fingerprint: '+result.ca_fingerprint+'\nSSH fingerprint: '+result.ssh_fingerprint+
            '\n\nThis replaces the printer CA, SSH host identity and trusted user keys. Web and SSH services will reload. Trust the restored CA before reconnecting; this page may disconnect.',{method:'bundle.restore',bundle,revision:state.revision});
    }); });
    $('identity-review').addEventListener('close',() => {
        const request = pending; pending = null;
        if ($('identity-review').returnValue !== 'confirm' || !request) return;
        void operation(async () => {
            const result = await call(request);
            if (request.method === 'bundle.export') {
                const bytes = Uint8Array.from(atob(result.content),c=>c.charCodeAt(0));
                download(result.filename,bytes,'application/zip'); report('Private identity backup downloaded.');
            } else if (request.method === 'bundle.restore') {
                $('identity-bundle-file').value = ''; state = null; controls();
                report('Identity restored. Services are reloading; reconnect using the restored CA and SSH identity.');
            } else { await refresh(); report('Trusted SSH public keys saved.'); }
        });
    });
    window.addEventListener('sv08-authority-changed',() => {
        ++epoch; state = null; pending = null; $('identity-review').close('cancel');
        $('identity-bundle-file').value = ''; $('identity-key-file').value = ''; $('identity-keys').value = '';
        controls(); if (window.sv08Session?.elevated && location.hash==='#identity') void refresh();
    });
    window.addEventListener('sv08-navigation-changed',event => {
        if (event.detail.to === 'identity') void refresh();
        else { pending = null; $('identity-review').close('cancel'); }
    });
    controls(); if (location.hash==='#identity') void window.sv08Session.ready.then(refresh);
})();
