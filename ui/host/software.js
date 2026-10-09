'use strict';
(() => {
    const $ = id => document.getElementById('software-'+id);
    const active = () => location.hash === '#software' && window.sv08Session?.elevated;
    let state=null, epoch=0, sequence=0, busy=false, review=null, timer=null, serviceDraft=null, unknownJob=null;
    const report = text => { $('status').textContent=text; };
    const bytes = value => Number.isFinite(Number(value)) ? (Number(value)/1048576).toFixed(1)+' MiB' : 'Unavailable';
    const selected = () => state?.catalog?.find(item => (item.id || item.package) === $('choice').value);
    async function call(request) {
        if(!active()) throw Error('Administrator access is required.');
        const generation=epoch;
        const raw=await cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_software.py'],{superuser:'require',err:'message'}).input(JSON.stringify(request));
        if(generation !== epoch || !active()) throw Error('Access changed. Refresh software.');
        const response=JSON.parse(raw);
        if(!response.ok) throw Error(response.error || 'Software operation failed.');
        return response.result;
    }
    function controls() {
        document.querySelectorAll('#software button,#software select,#software input').forEach(control => {control.disabled=busy || !active() || !state;});
        $('refresh').disabled=busy || !active();
        const item=selected();
        $('install').disabled ||= !item || !!item.installed;
        $('remove').disabled ||= !item || !item.installed;
        $('service').disabled ||= !item?.service || !item.installed;
        $('service-enabled').disabled ||= !item?.service || !item.installed;
        $('reconcile').disabled ||= !state?.capabilities?.reconcile?.available;
        $('export').disabled ||= !state?.reconciliation?.exports?.length;
        $('inspect').disabled ||= !unknownJob;
        $('confirm').disabled=busy || !active() || !review || review.available === false;
    }
    function detail() {
        const item=selected();
        $('title').textContent=item?.title || item?.label || item?.name || item?.package || item?.id || 'Choose software';
        $('detail').textContent=item ? (item.description || '')+' · '+(item.installed ? 'Installed' : 'Not installed') : 'No reviewed software is available.';
        $('dependencies').textContent='Packages: '+(item?.packages || [item?.package || item?.id].filter(Boolean)).join(', ')+' · '+(item?.dependencies?.length ? 'Dependencies: '+item.dependencies.join(', ') : 'Dependencies are resolved in review.');
        $('reason').textContent=(state?.capabilities?.install?.reason || '')+(state?.storage ? ' Root available: '+bytes(state.storage.root_free_bytes)+' · Data available: '+bytes(state.storage.data_free_bytes)+' · Data reserve: '+bytes(state.storage.data_reserve_bytes) : '');
        $('service-detail').textContent=item?.service ? 'Service: '+(item.service.unit || item.service)+' · '+(item.service_state?.ActiveState || item.service.active || 'Status unavailable') : 'This software has no configurable service.';
        $('service-enabled').checked=serviceDraft?.package === $('choice').value ? serviceDraft.enabled : item?.service_state?.UnitFileState === 'enabled' || !!item?.service?.enabled;
        controls();
    }
    function paint() {
        const choice=$('choice').value;
        $('choice').replaceChildren(...(state.catalog || []).map(item => {const option=document.createElement('option');option.value=item.id || item.package;option.textContent=item.title || item.label || item.name || option.value;return option;}));
        if([...$('choice').options].some(option => option.value === choice)) $('choice').value=choice;
        detail();
        $('customization').textContent=state.customization?.reason || (state.customized || state.customization?.customized ? 'This image has local changes and is protected from automatic replacement.' : 'Customization status is shown in the exported report.');
        $('reconciliation').textContent=state.reconciliation?.reason || 'Reconciliation availability is checked by the host.';
        const jobs=[...(state.jobs || (state.job ? [state.job] : []))].sort((a,b) => (a.created_at || 0)-(b.created_at || 0));
        paintJob(jobs.find(job => ['queued','running','unknown'].includes(job.status || job.state)) || jobs.at(-1));
    }
    function paintJob(job) {
        unknownJob=(job?.status || job?.state) === 'unknown' ? job.id : null;
        $('inspect').hidden=!unknownJob;
        $('job').hidden=!job;
        $('job-detail').textContent=job ? [job.id,job.state || job.status,job.phase,job.progress !== undefined ? job.progress+'%' : '',job.error || job.message || ''].filter(Boolean).join(' · ') : '';
        controls();
    }
    function poll() {
        clearTimeout(timer);
        if(active() && (state?.jobs || (state?.job ? [state.job] : [])).some(job => ['queued','running'].includes(job.status || job.state))) timer=setTimeout(() => {void refresh(false);},2000);
    }
    async function refresh(announce=true) {
        if(!active() || busy) return;
        const generation=epoch, attempt=++sequence;
        if(announce) report('Loading software…');
        try {
            const result=await call({method:'status'});
            if(generation !== epoch || attempt !== sequence) return;
            state=result;paint();
            if(announce) report('Software is ready.');
        } catch(error) {if(generation === epoch && attempt === sequence) {state=null;controls();report(error.message+' Refresh to check the durable operation result.');}}
        finally {if(generation === epoch) poll();}
    }
    async function plan(action,args={}) {
        if(!active() || busy || !state) return;
        const generation=epoch;++sequence;busy=true;controls();
        try {
            const inspection=action === 'acknowledge' ? await call({method:'inspect',id:args.id}) : null;
            const result=await call({method:'plan',action,arguments:args});
            if(generation !== epoch) return;
            review={...result,epoch};
            const preview=result.preview || {};
            const list=items => (items || []).map(item => typeof item === 'string' ? item : item.package+' '+(item.version || '')).join(', ') || 'None';
            $('review-title').textContent=action === 'reconcile' ? 'Review compatibility report' : 'Review '+action;
            $('review-detail').textContent='Install: '+list(preview.install)+'\nRemove: '+list(preview.remove)+'\nDownload: '+bytes(preview.download_bytes)+'\nInstalled size change: '+bytes(preview.installed_delta_bytes)+'\nRoot space required: '+bytes(preview.required_bytes)+'\nRoot space available: '+bytes(preview.root_free_bytes)+'\nData reserve: '+bytes(preview.data_reserve_bytes)+'\nData space available: '+bytes(preview.data_free_bytes)+((result.reason || preview.reason) ? '\n'+(result.reason || preview.reason) : '')+(action === 'service' ? '\nService: '+(args.enabled ? 'Start now and enable automatic start' : 'Stop now and disable automatic start') : '');
            if(inspection) {
                $('review-title').textContent='Review interrupted operation';
                $('review-detail').textContent=inspection.warning+'\nPackage check: '+(inspection.dpkg_audit || 'No unfinished package configuration reported.')+'\nService policy recovery: '+(inspection.policy_recovery_required ? (inspection.policy_recoverable ? 'Known blocking policy can be restored.' : 'Policy has changed; recovery is blocked.') : 'Not required')+'\nInstalled packages:\n'+(inspection.evidence?.inventory || []).map(row=>row.slice(0,3).join(' ')).join('\n')+'\nThis acknowledges the uncertain result. It will not repeat the package operation or clear customizations.';
            }
            $('review').returnValue='';$('review').showModal();
        } catch(error) {if(generation === epoch) report(error.message);}
        finally {if(generation === epoch) {busy=false;controls();}}
    }
    async function apply(action) {
        const generation=epoch;busy=true;controls();report('Submitting software change…');
        try {const job=await call({method:'apply',token:action.token,digest:action.digest});if(generation === epoch) {paintJob(job);report('Software change submitted.');}}
        catch(error) {if(generation === epoch) report(error.message+' Refresh to check whether the operation was accepted.');}
        finally {if(generation === epoch) {busy=false;controls();void refresh(false);}}
    }
    $('choice').addEventListener('change',() => {serviceDraft=null;detail();});
    $('service-enabled').addEventListener('change',() => {serviceDraft={package:$('choice').value,enabled:$('service-enabled').checked};});
    $('refresh').addEventListener('click',() => {review=null;$('review').close('cancel');void refresh();});
    for(const action of ['install','remove']) $(action).addEventListener('click',() => {const item=selected();if(item) void plan(action,{package:item.package || item.id});});
    $('service').addEventListener('click',() => {const item=selected();if(item) void plan('service',{package:item.package || item.id,enabled:$('service-enabled').checked});});
    $('inspect').addEventListener('click',() => {if(unknownJob) void plan('acknowledge',{id:unknownJob});});
    $('reconcile').addEventListener('click',() => void plan('reconcile'));
    $('review').addEventListener('close',() => {const action=review;review=null;controls();if($('review').returnValue === 'confirm' && action?.epoch === epoch && action.available !== false && active() && !busy) void apply(action);});
    $('export').addEventListener('click',async () => {
        const generation=epoch;busy=true;controls();
        try {const result=await call({method:'reconciliation-export',id:state.reconciliation.exports.at(-1)});if(generation !== epoch) return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)+'\n'],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='sv08-customization.json';link.click();setTimeout(() => URL.revokeObjectURL(url),1000);report('Customization report downloaded.');}
        catch(error) {if(generation === epoch) report(error.message);}
        finally {if(generation === epoch) {busy=false;controls();}}
    });
    function invalidate() {++epoch;++sequence;clearTimeout(timer);busy=false;state=null;review=null;serviceDraft=null;unknownJob=null;$('inspect').hidden=true;$('review').close('cancel');$('choice').replaceChildren();$('detail').textContent='';$('dependencies').textContent='';$('job').hidden=true;$('customization').textContent='';$('reconciliation').textContent='';controls();report(window.sv08Session?.elevated ? 'Loading software…' : 'Administrator access is required.');}
    window.addEventListener('sv08-authority-changed',() => {invalidate();if(active()) void refresh();});
    window.addEventListener('sv08-navigation-changed',event => {invalidate();if(event.detail.to === 'software') void refresh();});
    controls();if(location.hash === '#software') void window.sv08Session.ready.then(refresh);
})();
