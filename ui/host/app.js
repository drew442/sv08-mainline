'use strict';
const $ = id => document.getElementById(id);
let state, plan, busy = false, jobsBusy = false, refreshing = false;
// Production has only Cockpit's authenticated bridge. The test harness supplies
// that same interface; there is no unauthenticated HTTP fallback in this page.
async function request(message) {
    if (!window.cockpit) throw new Error('Open this page through the host’s authenticated administration console.');
    const process = cockpit.spawn(['/usr/bin/python3', '/usr/lib/sv08/sv08_admin.py'], {superuser: 'require', err: 'message'});
    const raw = await process.input(JSON.stringify(message));
    const response = JSON.parse(raw);
    if (!response.ok) { const error = new Error(response.error); error.acknowledged = true; throw error; }
    return response.result;
}
async function submissionError(error) {
    // A transport loss can still have a live helper. Only an acknowledged RPC
    // error plus a successful complete ledger read establishes no pending write.
    if (error.acknowledged && localStorage.getItem('sv08-image-submission')) {
        try { await request({method: 'jobs'}); localStorage.removeItem('sv08-image-submission'); } catch (_) { /* retain receipt */ }
    }
    notice(error.message);
}
function notice(message) { $('notice').textContent = message; }
function page(name, focus = true) {
    document.querySelectorAll('.page').forEach(p => { p.hidden = p.id !== name; });
    document.querySelectorAll('[data-page]').forEach(button => {
        if (button.dataset.page === name) button.setAttribute('aria-current', 'page');
        else button.removeAttribute('aria-current');
    });
    if (focus) $('main').focus();
}
function capability(action, button, reason) {
    const cap = state.capabilities[action];
    $(button).disabled = busy || jobsBusy || !cap.available;
    if (reason) $(reason).textContent = cap.available ? '' : cap.reason;
}
function options(id, values, empty) {
    const select = $(id); select.replaceChildren();
    if (!values.length) values = [{id: '', label: empty}];
    for (const item of values) {
        const option = document.createElement('option'); option.value = item.id; option.textContent = item.label; select.append(option);
    }
}
function render() {
    $('connection').textContent = 'Host connected';
    $('fixture').hidden = !state.fixture;
    $('release').textContent = state.boot.release;
    $('slot').textContent = `Running from slot ${state.boot.slot}`;
    $('mode').textContent = state.boot.mode === 'immutable' ? 'Immutable' : 'Writable';
    $('customized').textContent = state.boot.customized ? 'Local customizations preserved' : 'Standard release';
    $('space').textContent = `${(state.free_bytes / 1024 ** 3).toFixed(2)} GiB`;
    $('update-title').textContent = state.transaction ? `Update: ${state.transaction.phase}` : 'No update waiting';
    $('update-detail').textContent = state.pending ? `Slot ${state.pending.slot} · ${state.pending.release}. State is copied when the new release boots.` : 'The running system stays active until you select a verified release for the next boot.';
    $('slots').replaceChildren();
    for (const name of ['A', 'B']) {
        const record = state.slots[name], card = document.createElement('article'); card.className = 'card';
        const title = document.createElement('h2'); title.textContent = `Slot ${name}${name === state.boot.slot ? ' · Running' : ''}`;
        const text = document.createElement('p'); text.textContent = record ? `${record.release} · ${record.customized ? 'Customized — protected from replacement' : 'Standard release'}` : 'No registered state generation. Image availability must be verified before booting.';
        card.append(title, text); $('slots').append(card);
    }
    $('auto-update').checked = state.auto_update;
    document.querySelectorAll('[name=mode]').forEach(input => { input.checked = input.value === state.requested_mode; });
    $('hostname').value = state.hostname;
    options('image-choice', state.images, 'No verified uploaded image available');
    options('package-choice', state.catalog, 'No reviewed software catalog available');
    capability('policy.auto', 'save-auto'); capability('policy.mode', 'save-mode', 'mode-reason');
    capability('image.stage', 'stage-image', 'stage-reason'); capability('image.arm', 'arm-image', 'image-reason');
    capability('image.cancel', 'cancel-image'); capability('config.hostname', 'save-hostname', 'hostname-reason');
    capability('software.install', 'install-package', 'software-reason'); capability('software.remove', 'remove-package');
    if (!state.images.length) $('stage-image').disabled = true;
    if (!state.catalog.length) { $('install-package').disabled = true; $('remove-package').disabled = true; }
}
function renderJobs(result) {
    const pending = JSON.parse(localStorage.getItem('sv08-image-submission') || 'null');
    if (pending && result.jobs.some(job => job.id === pending.id)) localStorage.removeItem('sv08-image-submission');
    const unresolved = !!localStorage.getItem('sv08-image-submission');
    $('submission-pending').hidden = !unresolved; $('retry-submission').hidden = !unresolved;
    $('retry-submission').disabled = busy;
    jobsBusy = result.blocked || unresolved;
    $('jobs-summary').textContent = result.blocked ? 'An image operation is pending or needs reconciliation. You can close this page safely.' : 'No image operation is running.';
    $('jobs').replaceChildren();
    for (const job of result.jobs) {
        const item = document.createElement('p'); item.dataset.jobId = job.id; item.dataset.phase = job.phase;
        item.textContent = `${job.action} · ${job.phase} · ${job.id} — ${job.message}`;
        $('jobs').append(item);
    }
}
async function refresh() {
    if (refreshing) return;
    refreshing = true;
    try {
        // Job history renders before any state read. Transactions may hold the
        // state lock for minutes; never put status ahead of reconnect progress.
        const result = await request({method: 'jobs'}); renderJobs(result);
        if (result.blocked) {
            $('connection').textContent = 'Image worker status connected';
            document.querySelectorAll('main button:not([data-open]):not(#retry-submission)').forEach(b => { b.disabled = true; });
            return;
        }
        state = await request({method: 'status'}); render();
    } catch (error) { $('connection').textContent = 'Host unavailable'; notice(error.message); document.querySelectorAll('main button:not([data-open]):not(#retry-submission)').forEach(b => { b.disabled = true; }); }
    finally { refreshing = false; }
}
async function review(action, args = {}) {
    if (busy || jobsBusy || !state) return;
    try {
        plan = await request({method: 'plan', action, arguments: args});
        $('review-title').textContent = plan.title; $('review-effect').textContent = plan.effect;
        $('review-arguments').textContent = Object.entries(plan.arguments).map(([key, value]) => `${key}: ${value}`).join('\n') || 'Apply to the current update.';
        $('review').returnValue = 'cancel';
        $('review').showModal();
    } catch (error) { notice(error.message); await refresh(); }
}
$('review').addEventListener('close', async () => {
    if ($('review').returnValue !== 'confirm' || !plan || busy) { plan = null; return; }
    busy = true; render(); notice('Applying the reviewed change…');
    try {
        const image = plan.action.startsWith('image.');
        const message = image ? {method: 'image.submit', id: crypto.randomUUID().replaceAll('-', ''), plan} : {method: 'apply', plan};
        // Preserve lost-acknowledgement identity across page closure. Refresh only
        // observes server history; it never automatically submits this receipt.
        if (image) localStorage.setItem('sv08-image-submission', JSON.stringify(message));
        const result = await request(message);
        if (image) localStorage.removeItem('sv08-image-submission');
        notice(result.message || 'Change completed.');
    }
    catch (error) { await submissionError(error); }
    finally { plan = null; busy = false; await refresh(); }
});
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => page(b.dataset.page)));
document.querySelectorAll('[data-open]').forEach(b => b.addEventListener('click', () => page(b.dataset.open)));
$('refresh').addEventListener('click', refresh);
$('retry-submission').addEventListener('click', async () => {
    if (busy) return;
    const pending = JSON.parse(localStorage.getItem('sv08-image-submission') || 'null');
    if (!pending) return;
    busy = true;
    try { const result = await request(pending); notice(result.message); localStorage.removeItem('sv08-image-submission'); }
    catch (error) { await submissionError(error); }
    finally { busy = false; await refresh(); }
});
$('save-auto').addEventListener('click', () => review('policy.auto', {enabled: $('auto-update').checked}));
$('save-mode').addEventListener('click', () => review('policy.mode', {mode: document.querySelector('[name=mode]:checked').value}));
$('stage-image').addEventListener('click', () => review('image.stage', {digest: $('image-choice').value}));
$('arm-image').addEventListener('click', () => review('image.arm'));
$('cancel-image').addEventListener('click', () => review('image.cancel'));
$('install-package').addEventListener('click', () => review('software.install', {package: $('package-choice').value}));
$('remove-package').addEventListener('click', () => review('software.remove', {package: $('package-choice').value}));
$('save-hostname').addEventListener('click', () => review('config.hostname', {hostname: $('hostname').value}));
refresh();

setInterval(refresh, 1500);
