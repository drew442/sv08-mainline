'use strict';
const $ = id => document.getElementById(id);
let authorityGeneration = 0;
let state, plan, busy = false, jobsBusy = false, refreshing = false;
// Production has only Cockpit's authenticated bridge. The test harness supplies
// that same interface; there is no unauthenticated HTTP fallback in this page.
async function request(message) {
    if (['status', 'jobs', 'upload.list'].includes(message.method)) return sv08View('host', message.method);
    if (!window.cockpit) throw new Error('Open this page through the host’s authenticated administration console.');
    if (!window.sv08Session || !await sv08Session.ready || !sv08Session.elevated) throw Object.assign(new Error('Administrator access is required. Use Administrator access to continue.'), {noticeKind:'authorization'});
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
    notice(error.message, localStorage.getItem('sv08-image-submission') ? 'uncertain' : 'operation');
}
// Only the owner of a transient notice can clear it. Operation outcomes and
// uncertain receipts survive successful background status reads.
const noticeSlots = new Map();
function paintNotices() {
    const active=['uncertain','operation','authorization','connectivity'].filter(kind=>noticeSlots.get(kind));
    $('notice').textContent=active.map(kind=>noticeSlots.get(kind)).join('\n');
    $('notice').dataset.kind=active[0] || 'status';
}
function notice(message, kind = 'operation') { noticeSlots.set(kind,message);paintNotices(); }
function clearStatusNotice() {noticeSlots.delete('authorization');noticeSlots.delete('connectivity');paintNotices();}


function page(name, focus = true) {
    if (window.sv08Navigation) { sv08Navigation.go(name); return; }
    document.querySelectorAll('.page').forEach(p => { p.hidden = p.id !== name; });
    document.querySelectorAll('[data-page]').forEach(button => {
        if (button.dataset.page === name) button.setAttribute('aria-current', 'page');
        else button.removeAttribute('aria-current');
    });
    if (focus) $('main').focus();
}
function capability(action, button, reason) {
    const cap = state.capabilities[action] || {available:false, reason:'This host does not support this operation.'};
    $(button).disabled = busy || jobsBusy || !sv08Session.elevated || !cap.available;
    if (reason) $(reason).textContent = [!cap.available ? cap.reason : '', !sv08Session.elevated ? 'Administrator access is required to review this change.' : ''].filter(Boolean).join(' ');
}
const updateChecks = ['check_compatibility', 'check_customization', 'check_version', 'allow_downgrade', 'allow_untrusted_provenance'];
function updateOptions(prefix) {
    return Object.fromEntries(updateChecks.map(name => [name, $(prefix+'-'+name.replaceAll('_','-'))?.checked ?? false]));
}
function writeUpdateOptions(value) {
    for (const name of updateChecks) {
        const input = $('auto-'+name.replaceAll('_','-'));
        if (input) input.checked = value[name];
    }
}
// Draft state is local to each editable control, separate from fresh host status.
const drafts = {
    'policy.auto': {field: 'auto_update', argument: 'enabled', read: () => $('auto-update').checked, write: value => { $('auto-update').checked = value; }},
    'policy.update': {field: 'update_policy', argument: 'options', read: () => JSON.stringify(updateOptions('auto')), write: value => writeUpdateOptions(value || {check_version:true,check_compatibility:true,check_customization:true})},
    'policy.mode': {field: 'requested_mode', argument: 'mode', read: () => document.querySelector('[name=mode]:checked').value,
        write: value => document.querySelectorAll('[name=mode]').forEach(input => { input.checked = input.value === value; })},
};
function renderDrafts() {
    for (const draft of Object.values(drafts)) {
        // Also detect edits made by autofill or input methods without an event.
        if (draft.initialized && draft.read() !== draft.painted) draft.dirty = true;
        if (!draft.dirty) {
            draft.write(state[draft.field]); draft.painted = draft.read();
        }
        draft.initialized = true;
    }
}
function appliedDraft(reviewed) {
    const draft = drafts[reviewed.action];
    if (draft && draft.read() === (reviewed.action === 'policy.update' ? JSON.stringify(reviewed.arguments.options) : reviewed.arguments[draft.argument])) {
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
    clearStatusNotice();
    $('fixture').hidden = !state.fixture;
    $('release').textContent = state.boot.release;
    $('slot').textContent = `Running from slot ${state.boot.slot}`;
    $('mode').textContent = state.boot.mode === 'immutable' ? 'Immutable' : 'Writable';
    $('customized').textContent = state.boot.customized ? 'Local customizations preserved' : 'Standard release';
    const modeName = value => value === 'writable' ? 'Writable' : value === 'immutable' ? 'Immutable' : 'Unavailable';
    $('settings-current-mode').textContent = modeName(state.boot.mode);
    $('settings-next-mode').textContent = modeName(state.requested_mode)+(state.requested_mode === state.boot.mode ? ' · same as running now' : ' · takes effect after restart');
    $('overview-next-mode').textContent = state.requested_mode === state.boot.mode ? '' : 'Next boot: '+modeName(state.requested_mode);
    $('mode-reason').textContent = !sv08Session.elevated ? 'Administrator access is required to save a mode change. You can inspect the current mode.' : '';
    $('space').textContent = `${(state.free_bytes / 1024 ** 3).toFixed(2)} GiB`;
    const update=sv08Presentation.update(state);
    $('update-title').textContent=update.title;
    $('update-detail').textContent=update.detail;
    $('update-status-panel').dataset.tone=update.tone;
    sv08Presentation.status($('update-status'),{error:'Failed',success:'Completed',warning:'Pending / action required',neutral:'Current state'}[update.tone],update.tone,update.icon);
    const feed=state.feed_status;
    $('update-feed').hidden=!feed;
    if(feed){
        const messages={'reboot-queued':'A restart was requested; this does not establish boot health.','reboot-observed':'A restart was observed; this does not establish update success.','reboot-uncertain':'Restart acknowledgment was uncertain. No automatic retry will be sent.','reboot-suppressed':'Automatic restart was suppressed. Check the current boot selection.','awaiting-health-reconciliation':'The previous check awaited boot health reconciliation.','armed-next-boot':'An update was selected for a normal boot. Check the current boot selection.',blocked:'Blocked: '+(feed.reason || 'reason unavailable')};
        $('update-feed').textContent='Last automatic check: '+(messages[feed.result] || 'Reported '+(feed.result || 'unknown result')+'. Check the current transaction above.');
    }
    $('slots').replaceChildren();
    for (const name of ['A', 'B']) {
        const record = state.slots[name], card = document.createElement('article'); card.className = 'card';
        const title = document.createElement('h2'); title.textContent = name === state.boot.slot ? 'Running release' : 'Fallback / update target';
        const details = document.createElement('details'), label=document.createElement('summary'); label.textContent='Storage slot '+name;details.append(label);
        const text = document.createElement('p'); text.textContent = record ? `${record.release} · ${record.customized ? 'Customized — protected from replacement' : 'Standard release'}` : 'No registered state generation. Image availability must be verified before booting.';
        card.append(title, text, details); $('slots').append(card);
    }
    if ($('manual-update-step')) sv08Presentation.status($('manual-update-step'),state.transaction || state.pending ? update.title+'. '+update.detail : state.images.length ? 'Upload authenticated. Review installation to verify the full payload and prepare the inactive image.' : 'Start by uploading a signed OS bundle.',update.tone,update.icon);
    renderDrafts();
    options('image-choice', state.images, 'No verified uploaded image available');
    capability('policy.update', 'save-update-policy'); capability('policy.auto', 'save-auto'); capability('policy.mode', 'save-mode', 'mode-reason');
    capability('image.stage', 'stage-image', 'stage-reason'); capability('image.arm', 'arm-image', 'image-reason');
    capability('image.cancel', 'cancel-image');
    if (!$('image-choice').value) $('stage-image').disabled = true;
}
function renderJobs(result) {
    const pending = JSON.parse(localStorage.getItem('sv08-image-submission') || 'null');
    if (pending && result.jobs.some(job => job.id === pending.id)) localStorage.removeItem('sv08-image-submission');
    const unresolved = !!localStorage.getItem('sv08-image-submission');
    if(!unresolved){noticeSlots.delete('uncertain');paintNotices();}
    $('submission-pending').hidden = !unresolved; $('retry-submission').hidden = !unresolved;
    $('retry-submission').disabled = !sv08Session.elevated || busy;
    const previousJobsBusy=jobsBusy;
    jobsBusy = result.blocked || unresolved;
    if(jobsBusy!==previousJobsBusy)scheduleRefresh();
    const indicator=$('operation-indicator');
    if(indicator){indicator.hidden=!(jobsBusy || localStorage.getItem('sv08-history-maintenance'));indicator.textContent=unresolved ? 'Update acknowledgment uncertain — check its receipt' : result.blocked ? 'Update operation needs attention — view progress / outcome' : 'History maintenance acknowledgment uncertain — check its receipt';}

    $('jobs-summary').textContent = result.blocked ? 'An image operation is pending or needs outcome review. You can close this page safely.' : 'No image operation is running.';
    $('history-capacity').textContent = `Active ${result.active ?? (result.capacity-result.remaining)}/${result.capacity}; archives ${result.archives ?? 0}/8; retained ${result.total ?? result.jobs.length}/${result.total_capacity ?? 1152}. ${result.maintenance_reason || ''}`;
    $('history-maintenance').disabled = !sv08Session.elevated || busy || !result.maintenance_available;
    $('history-retry').hidden = !localStorage.getItem('sv08-history-maintenance');
    $('history-retry').disabled = !sv08Session.elevated || busy;
    const focusedJob = $('jobs').contains(document.activeElement) ? document.activeElement.closest('[data-job-id]')?.dataset.jobId : null;
    $('jobs').replaceChildren();
    for (const job of result.jobs) {
        const item = document.createElement('p'); item.dataset.jobId = job.id; item.dataset.phase = job.phase; item.tabIndex = -1;
        item.textContent = `${job.action} · ${job.phase} · ${job.id} — ${job.message}`;
        sv08Presentation.status(item,item.textContent,job.phase==='failed'?'error':job.phase==='succeeded'?'success':['interrupted','refused'].includes(job.phase)?'warning':'neutral',job.phase==='failed'?'error':job.phase==='succeeded'?'check':['interrupted','refused'].includes(job.phase)?'clock':'info');
        if (job.phase === 'interrupted' && !job.disposition) {
            const button = document.createElement('button');
            button.textContent = 'Inspect unknown outcome'; button.dataset.inspectJob = job.id;
            button.disabled = !sv08Session.elevated || busy;
            button.addEventListener('click', () => inspectJob(job.id));
            item.append(button);
        }
        $('jobs').append(item);
        if (focusedJob === job.id) item.focus({preventScroll:true});
    }
    if (focusedJob && !result.jobs.some(job => job.id === focusedJob)) $('image-history-title').focus({preventScroll:true});
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
            $('connection').textContent = 'Image worker status connected'; clearStatusNotice();
            document.querySelectorAll('main button:not([data-open]):not(#retry-submission):not([data-inspect-job]):not(#printer button):not(#definition-sources button):not(#printer-connections button):not(#definitions button):not(#identity button):not(#mainsail-access button):not(#network button):not(#software button)').forEach(b => { b.disabled = true; });
            return;
        }
        const next = await request({method: 'status'});
        if (generation !== authorityGeneration) return;
        state = next; render();
        document.querySelectorAll('#settings input, #images input').forEach(control => {control.disabled=!sv08Session.elevated;});
        if (!sv08Session.elevated) document.querySelectorAll('#images button:not([data-open]), #settings button:not([data-open]), #recovery button:not([data-open])').forEach(control => {control.disabled=true;});
    } catch (error) { if (generation !== authorityGeneration) return; $('connection').textContent = 'System status unavailable'; $('settings-current-mode').textContent = 'Unavailable · refresh to check'; $('settings-next-mode').textContent = 'Unavailable · refresh to check'; notice(error.message, error.noticeKind || 'connectivity'); document.querySelectorAll('main button:not([data-open]):not(#retry-submission):not([data-inspect-job]):not(#printer button):not(#definition-sources button):not(#printer-connections button):not(#definitions button):not(#identity button):not(#mainsail-access button):not(#network button):not(#software button)').forEach(b => { b.disabled = true; }); }
    finally { refreshing = false; }
}
async function inspectJob(id) {
    if (busy) return;
    const generation = authorityGeneration;
    try {
        const result = await request({method: 'image.inspect', id});
        if (generation !== authorityGeneration || !result.plan) return;
        plan = result.plan;
        $('review-title').textContent = 'Retain unknown outcome';
        $('review-effect').textContent = result.message;
        $('review-arguments').textContent = JSON.stringify(result.evidence, null, 2);
        $('review').returnValue = 'cancel'; $('review').showModal();
    } catch (error) { notice(error.message); }
}
async function review(action, args = {}) {
    if (busy || jobsBusy || !state) return;
    const generation = authorityGeneration;
    try {
        const reviewed = await request({method: 'plan', action, arguments: args});
        if (generation !== authorityGeneration) return;
        plan = reviewed; notice('Review the change before applying.');
        $('review-title').textContent = plan.title; $('review-effect').textContent = plan.effect;
        $('review-arguments').textContent = Object.entries(plan.arguments).map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}`).join('\n') || 'Apply to the current update.';
        $('review').returnValue = 'cancel';
        $('review').showModal();
    } catch (error) { notice(error.message); await refresh(); }
}
$('review').addEventListener('close', async () => {
    if ($('review').returnValue !== 'confirm' || !plan || busy) { plan = null; return; }
    const reviewed = plan;
    busy = true; $('history-maintenance').disabled = true; $('history-retry').disabled = true; if (state) render(); notice('Applying the reviewed change…');
    try {
        const maintenance = reviewed.kind === 'history-maintenance-v2';
        const disposition = reviewed.kind === 'retain-unknown-v1';
        const image = !maintenance && !disposition && reviewed.action.startsWith('image.');
        const message = maintenance ? {method: 'history.apply', plan: reviewed} : disposition ? {method: 'image.dispose', plan: reviewed} : image ? {method: 'image.submit', id: crypto.randomUUID().replaceAll('-', ''), plan: reviewed} : {method: 'apply', plan: reviewed};
        // Preserve lost-acknowledgement identity across page closure. Refresh only
        // observes server history; it never automatically submits this receipt.
        if (image) localStorage.setItem('sv08-image-submission', JSON.stringify(message));
        if (maintenance) localStorage.setItem('sv08-history-maintenance', JSON.stringify(message));
        const result = await request(message);
        if (image) localStorage.removeItem('sv08-image-submission');
        if (maintenance) localStorage.removeItem('sv08-history-maintenance');
        else if (!disposition && !maintenance) appliedDraft(reviewed);
        notice(result.message || 'Change completed.');
    }
    catch (error) { await submissionError(error); }
    finally { plan = null; busy = false; await refresh(); }
});
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => page(b.dataset.page)));
document.querySelectorAll('[data-open]').forEach(b => b.addEventListener('click', () => page(b.dataset.open)));
$('operation-indicator').addEventListener('click', () => {
    // Navigation only: receipt reconciliation and all mutations stay explicit.
    page('images');
    const pending = JSON.parse(localStorage.getItem('sv08-image-submission') || 'null');
    const operations = Array.from($('jobs').querySelectorAll('[data-job-id]'));
    const relevant = operations.find(item => item.dataset.jobId === pending?.id)
        || operations.find(item => !['succeeded', 'failed'].includes(item.dataset.phase));
    const target = relevant || $('image-history-title');
    target.focus({preventScroll:true});
    target.scrollIntoView({block:'center'});
});

$('refresh').addEventListener('click', refresh);
$('history-retry').addEventListener('click', async () => {
    if (busy) return;
    const pending = JSON.parse(localStorage.getItem('sv08-history-maintenance') || 'null');
    if (!pending || pending.method !== 'history.apply') return;
    busy = true;
    try { const result = await request(pending); localStorage.removeItem('sv08-history-maintenance'); notice(result.message); }
    catch (error) { notice(error.message); }
    finally { busy = false; await refresh(); }
});
$('history-maintenance').addEventListener('click', async () => {
    if (busy) return;
    const generation = authorityGeneration;
    try {
        const result = await request({method: 'history.review'});
        if (generation !== authorityGeneration) return;
        plan = result.plan;
        $('review-title').textContent = 'Preserve image history';
        $('review-effect').textContent = result.message;
        $('review-arguments').textContent = `${plan.operation}: preserve ${plan.ids.length} original receipts. Revision ${plan.revision}`;
        $('review').returnValue = 'cancel'; $('review').showModal();
    } catch (error) { notice(error.message); }
});
$('retry-submission').addEventListener('click', async () => {
    if (busy) return;
    const pending = JSON.parse(localStorage.getItem('sv08-image-submission') || 'null');
    if (!pending) return;
    busy = true;
    try { const result = await request(pending); notice(result.message); localStorage.removeItem('sv08-image-submission'); }
    catch (error) { await submissionError(error); }
    finally { busy = false; await refresh(); }
});
for (const [selector, action] of [['#auto-update', 'policy.auto'], ['[name=mode]', 'policy.mode'], ['[id^=auto-check-],#auto-allow-downgrade', 'policy.update']]) {
    document.querySelectorAll(selector).forEach(input => {
        for (const event of ['input', 'change']) input.addEventListener(event, () => { drafts[action].dirty = true; });
    });
}
for (const id of ['image-choice']) $(id).addEventListener('change', () => { if (state) render(); });
$('save-auto').addEventListener('click', () => review('policy.auto', {enabled: $('auto-update').checked}));
$('save-update-policy').addEventListener('click', () => review('policy.update', {options: updateOptions('auto')}));
$('save-mode').addEventListener('click', () => review('policy.mode', {mode: document.querySelector('[name=mode]:checked').value}));
$('stage-image').addEventListener('click', () => review('image.stage', {digest: $('image-choice').value, options: updateOptions('manual')}));
$('arm-image').addEventListener('click', () => review('image.arm'));
$('cancel-image').addEventListener('click', () => review('image.cancel'));
window.addEventListener('sv08-navigation-changed', () => { ++authorityGeneration; plan = null; if ($('review').open) $('review').close('cancel'); });
window.addEventListener('sv08-authority-changed', () => {
    ++authorityGeneration;
    plan = null;
    if ($('review').open) $('review').close('cancel');
    if (sv08Session.available) void refresh();
    else { $('connection').textContent = 'Administrator access required'; notice('Administrator access is required. Authorize to continue.', 'authorization'); document.querySelectorAll('main button:not([data-open]):not([data-page])').forEach(b=>{if(!b.closest('#printer, #definition-sources, #printer-connections, #definitions, #identity, #mainsail-access, #network, #software'))b.disabled=true;}); }
});
let refreshTimer;
function scheduleRefresh(immediate=false) {
    clearTimeout(refreshTimer);
    const urgent=jobsBusy || busy || !!localStorage.getItem('sv08-image-submission') || !!localStorage.getItem('sv08-history-maintenance');
    const hostPage=['overview','images','settings','recovery'].includes(window.sv08Navigation?.current || location.hash.slice(1));
    const interval=urgent ? 1500 : document.hidden ? 30000 : hostPage ? 5000 : 15000;
    refreshTimer=setTimeout(async()=>{if(window.sv08Session?.available)await refresh();scheduleRefresh();},immediate?0:interval);
}
window.addEventListener('sv08-navigation-changed',()=>scheduleRefresh(true));
window.addEventListener('sv08-authority-changed',()=>scheduleRefresh());
document.addEventListener('visibilitychange',()=>scheduleRefresh(!document.hidden));
void refresh().finally(()=>scheduleRefresh());
