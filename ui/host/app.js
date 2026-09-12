'use strict';
const $ = id => document.getElementById(id);
let authorityGeneration = 0;
let state, plan, busy = false, jobsBusy = false, refreshing = false;
// Production has only Cockpit's authenticated bridge. The test harness supplies
// that same interface; there is no unauthenticated HTTP fallback in this page.
async function request(message) {
    if (!window.cockpit) throw new Error('Open this page through the host’s authenticated administration console.');
    if (!window.sv08Session || !await sv08Session.ready || !sv08Session.elevated) throw new Error('Administrator access is required. Use Administrator access to continue.');
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
// Draft state is local to each editable control, separate from fresh host status.
const drafts = {
    'policy.auto': {field: 'auto_update', argument: 'enabled', read: () => $('auto-update').checked, write: value => { $('auto-update').checked = value; }},
    'policy.mode': {field: 'requested_mode', argument: 'mode', read: () => document.querySelector('[name=mode]:checked').value,
        write: value => document.querySelectorAll('[name=mode]').forEach(input => { input.checked = input.value === value; })},
    'config.hostname': {field: 'hostname', argument: 'hostname', read: () => $('hostname').value, write: value => { $('hostname').value = value; }},
};
function renderDrafts() {
    for (const draft of Object.values(drafts)) {
        // Also detect edits made by autofill or input methods without an event.
        if (draft.initialized && draft.read() !== draft.painted) draft.dirty = true;
        if (!draft.dirty) {
            draft.write(state[draft.field]); draft.painted = state[draft.field];
        }
        draft.initialized = true;
    }
}
function appliedDraft(reviewed) {
    const draft = drafts[reviewed.action];
    if (draft && draft.read() === reviewed.arguments[draft.argument]) {
        draft.dirty = false; draft.painted = draft.read();
    }
}
function options(id, values, empty) {
    const select = $(id), previous = select.value, initialized = select.dataset.initialized === 'true';
    const retained = values.some(item => item.id === previous);
    if (previous && !retained) select.dataset.missing = 'true';
    if (retained) delete select.dataset.missing;
    if (!values.length || initialized && !retained) {
        const label = select.dataset.missing ? 'Previous selection is unavailable. Choose another item.' : (values.length ? 'Choose an item.' : empty);
        values = [{id: '', label}, ...values];
    }
    const unchanged = select.options.length === values.length && values.every((item, index) => select.options[index].value === item.id && select.options[index].textContent === item.label);
    select.dataset.initialized = 'true';
    if (unchanged) return; // Preserve native dropdown/focus state across ordinary polls.
    select.replaceChildren();
    for (const item of values) {
        const option = document.createElement('option'); option.value = item.id; option.textContent = item.label; select.append(option);
    }
    if (retained) select.value = previous;
    else if (initialized) select.value = '';
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
    renderDrafts();
    options('image-choice', state.images, 'No verified uploaded image available');
    options('package-choice', state.catalog, 'No reviewed software catalog available');
    capability('policy.auto', 'save-auto'); capability('policy.mode', 'save-mode', 'mode-reason');
    capability('image.stage', 'stage-image', 'stage-reason'); capability('image.arm', 'arm-image', 'image-reason');
    capability('image.cancel', 'cancel-image'); capability('config.hostname', 'save-hostname', 'hostname-reason');
    capability('software.install', 'install-package', 'software-reason'); capability('software.remove', 'remove-package');
    if (!$('image-choice').value) $('stage-image').disabled = true;
    if (!$('package-choice').value) { $('install-package').disabled = true; $('remove-package').disabled = true; }
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
    refreshing = true; const generation = authorityGeneration;
    try {
        // Job history renders before any state read. Transactions may hold the
        // state lock for minutes; never put status ahead of reconnect progress.
        const result = await request({method: 'jobs'});
        if (generation !== authorityGeneration) return;
        renderJobs(result);
        if (result.blocked) {
            $('connection').textContent = 'Image worker status connected';
            document.querySelectorAll('main button:not([data-open]):not(#retry-submission)').forEach(b => { b.disabled = true; });
            return;
        }
        const next = await request({method: 'status'});
        if (generation !== authorityGeneration) return;
        state = next; render();
    } catch (error) { $('connection').textContent = 'Host unavailable'; notice(error.message); document.querySelectorAll('main button:not([data-open]):not(#retry-submission)').forEach(b => { b.disabled = true; }); }
    finally { refreshing = false; }
}
async function review(action, args = {}) {
    if (busy || jobsBusy || !state) return;
    const generation = authorityGeneration;
    try {
        const reviewed = await request({method: 'plan', action, arguments: args});
        if (generation !== authorityGeneration) return;
        plan = reviewed; notice('Review the change before applying.');
        $('review-title').textContent = plan.title; $('review-effect').textContent = plan.effect;
        $('review-arguments').textContent = Object.entries(plan.arguments).map(([key, value]) => `${key}: ${value}`).join('\n') || 'Apply to the current update.';
        $('review').returnValue = 'cancel';
        $('review').showModal();
    } catch (error) { notice(error.message); await refresh(); }
}
$('review').addEventListener('close', async () => {
    if ($('review').returnValue !== 'confirm' || !plan || busy) { plan = null; return; }
    const reviewed = plan;
    busy = true; render(); notice('Applying the reviewed change…');
    try {
        const image = reviewed.action.startsWith('image.');
        const message = image ? {method: 'image.submit', id: crypto.randomUUID().replaceAll('-', ''), plan: reviewed} : {method: 'apply', plan: reviewed};
        // Preserve lost-acknowledgement identity across page closure. Refresh only
        // observes server history; it never automatically submits this receipt.
        if (image) localStorage.setItem('sv08-image-submission', JSON.stringify(message));
        const result = await request(message);
        if (image) localStorage.removeItem('sv08-image-submission');
        else appliedDraft(reviewed);
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
for (const [selector, action] of [['#auto-update', 'policy.auto'], ['[name=mode]', 'policy.mode'], ['#hostname', 'config.hostname']]) {
    document.querySelectorAll(selector).forEach(input => {
        for (const event of ['input', 'change']) input.addEventListener(event, () => { drafts[action].dirty = true; });
    });
}
for (const id of ['image-choice', 'package-choice']) $(id).addEventListener('change', () => { if (state) render(); });
$('save-auto').addEventListener('click', () => review('policy.auto', {enabled: $('auto-update').checked}));
$('save-mode').addEventListener('click', () => review('policy.mode', {mode: document.querySelector('[name=mode]:checked').value}));
$('stage-image').addEventListener('click', () => review('image.stage', {digest: $('image-choice').value}));
$('arm-image').addEventListener('click', () => review('image.arm'));
$('cancel-image').addEventListener('click', () => review('image.cancel'));
$('install-package').addEventListener('click', () => review('software.install', {package: $('package-choice').value}));
$('remove-package').addEventListener('click', () => review('software.remove', {package: $('package-choice').value}));
$('save-hostname').addEventListener('click', () => review('config.hostname', {hostname: $('hostname').value}));
window.addEventListener('sv08-authority-changed', () => {
    ++authorityGeneration;
    plan = null;
    if ($('review').open) $('review').close('cancel');
    if (sv08Session.elevated) void refresh();
    else $('connection').textContent = 'Administrator access required';
});
refresh();

setInterval(refresh, 1500);
