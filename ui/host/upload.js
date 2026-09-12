'use strict';
// One File slice and one unacknowledged 64 KiB chunk. Cockpit input has no drain
// promise; server acknowledgements, not input() return values, advance the file.
let uploadReview = null, uploadProcess = null, uploadActive = false;
const uploadText = text => { $('upload-status').textContent = text; };
async function uploadListing() {
    const generation = authorityGeneration;
    try {
        const result = await request({method: 'upload.list'});
        if (generation !== authorityGeneration) return;
        const signature = JSON.stringify([result.objects, result.busy, uploadActive]);
        if ($('upload-list').dataset.signature !== signature) {
        $('upload-list').dataset.signature = signature;
        const hadFocus = $('upload-list').contains(document.activeElement);
        $('upload-list').replaceChildren();
        for (const item of result.objects) {
            const row = document.createElement('p');
            row.textContent = `${item.name} · ${item.state}${item.bytes === undefined ? '' : ' · '+item.bytes+' bytes'} `;
            const button = document.createElement('button'); button.textContent = 'Review removal';
            button.disabled = result.busy || uploadActive || item.bytes === undefined;
            button.addEventListener('click', () => reviewRemoval(item.name));
            row.append(button); $('upload-list').append(row);
        }
        if (hadFocus) { $('upload-storage').tabIndex = -1; $('upload-storage').focus(); }
        }
        $('upload-storage').textContent = result.message;
        $('review-upload').disabled = uploadActive || result.busy;
    } catch (error) { if (generation !== authorityGeneration) return; $('upload-storage').textContent = error.message; $('review-upload').disabled = true; }
}
async function reviewRemoval(name) {
    const generation = authorityGeneration;
    try {
        const reviewed = await request({method:'upload.cleanup-plan', name});
        if (generation !== authorityGeneration) return;
        uploadReview = {kind:'cleanup', plan:reviewed};
        $('upload-review-title').textContent = 'Remove this managed upload?';
        $('upload-review-detail').textContent = `${name}\n${reviewed.object.bytes} bytes\nRemove only this reviewed object. No OS transaction is cancelled.`;
        $('upload-review').returnValue = 'cancel'; $('upload-review').showModal();
    } catch(error) { uploadText(error.message); }
}
$('review-upload').addEventListener('click', async () => {
    const file = $('bundle-file').files[0], generation = authorityGeneration;
    if (!file || uploadActive) return;
    try {
        const reviewed = await request({method:'upload.plan', name:file.name, size:file.size});
        if (generation !== authorityGeneration) return;
        uploadReview = {kind:'upload', plan:reviewed, file};
        $('upload-review-title').textContent = 'Upload this OS bundle?';
        $('upload-review-detail').textContent = `${file.name}\n${file.size} bytes\nAuthenticate its signed manifest and store it privately. Image staging requires a separate review.`;
        $('upload-review').returnValue = 'cancel'; $('upload-review').showModal();
    } catch(error) { uploadText(error.message); }
});
function transferBundle(file, reviewed) {
    return new Promise((resolve, reject) => {
        const encoder = new TextEncoder(), decoder = new TextDecoder('utf-8', {fatal:true});
        let buffer = '', totalOutput = 0, sent = 0, received = 0, ready = false, complete = null, ended = false, sending = false;
        let inactivity;
        const process = cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin_upload.py'], {superuser:'require', binary:true, err:'message'});
        uploadProcess = process;
        const overall = setTimeout(() => fail(Error('Upload deadline reached; inspect managed storage before retrying.')), 1805000);
        const reset = () => { clearTimeout(inactivity); inactivity = setTimeout(() => fail(Error('Upload response timed out; inspect managed storage.')), 65000); };
        const finish = () => { ended = true; clearTimeout(inactivity); clearTimeout(overall); uploadProcess = null; };
        const fail = error => { if (ended) return; finish(); process.close('terminated'); reject(error); };
        async function sendNext() {
            if (sending || ended) return;
            if (received === file.size) { process.input(null); uploadText(`${received} / ${file.size} bytes acknowledged. Checking signed manifest…`); return; }
            sending = true;
            try {
                const chunk = new Uint8Array(await file.slice(sent, Math.min(sent+65536,file.size)).arrayBuffer());
                if (ended) return;
                sent += chunk.length; process.input(chunk, true);
            } catch(error) { fail(error); }
            finally { sending = false; }
        }
        process.stream(data => {
            if (ended) return;
            try {
                totalOutput += data.length;
                if (totalOutput > 2097152) throw Error('Upload response exceeds its budget');
                buffer += decoder.decode(new Uint8Array(data), {stream:true});
                if (buffer.length > 16384) throw Error('Upload response record exceeds its budget');
                let newline;
                while ((newline = buffer.indexOf('\n')) >= 0) {
                    const record = JSON.parse(buffer.slice(0,newline)); buffer = buffer.slice(newline+1); reset();
                    if (record.type === 'error') throw Error(record.error);
                    if (record.type === 'ready' && !ready && record.chunk === 65536) { ready = true; void sendNext(); }
                    else if (record.type === 'ack' && ready && !complete && Number.isSafeInteger(record.received) && record.received === sent && record.received > received) {
                        received = record.received; $('upload-progress').value = received / file.size;
                        uploadText(`${received} / ${file.size} bytes acknowledged`); void sendNext();
                    } else if (record.type === 'complete' && received === file.size && !complete && record.result?.proof?.full_payload_verified === false) complete = record.result;
                    else throw Error('Invalid upload acknowledgement');
                }
            } catch(error) { fail(error); }
        });
        process.then(() => {
            if (ended) return;
            try {
                if (!complete || buffer || decoder.decode()) throw Error('Completion not acknowledged; inspect managed storage. No transfer will be replayed.');
                finish(); resolve(complete);
            } catch (error) { fail(error); }
        }, error => { if (!ended) fail(Error('Upload connection lost or cancelled; inspect managed storage. '+error.message)); });
        reset(); process.input(encoder.encode(JSON.stringify(reviewed)+'\n'), true);
    });
}
$('upload-review').addEventListener('close', async () => {
    const reviewed = uploadReview; uploadReview = null;
    if ($('upload-review').returnValue !== 'confirm' || !reviewed || uploadActive) return;
    uploadActive = true; $('review-upload').disabled = true;
    try {
        if (reviewed.kind === 'cleanup') uploadText((await request({method:'upload.cleanup',plan:reviewed.plan})).message);
        else {
            $('cancel-upload').hidden = false; $('cancel-upload').disabled = false; $('upload-progress').value = 0;
            const result = await transferBundle(reviewed.file, reviewed.plan);
            uploadText(`${result.message}\nRelease: ${result.proof.release}\nProfile: ${result.proof.compatible}\nSHA-256: ${result.proof.bundle_sha256}`);
        }
    } catch(error) { uploadText(error.message); }
    finally { uploadActive = false; $('cancel-upload').hidden = true; await uploadListing(); await refresh(); }
});
$('cancel-upload').addEventListener('click', () => { uploadProcess?.close('terminated'); uploadText('Cancellation requested. Inspect managed storage; no OS transaction was cancelled.'); });
window.addEventListener('sv08-authority-changed', () => {
    uploadReview = null;
    if ($('upload-review').open) $('upload-review').close('cancel');
    if (!sv08Session.elevated) uploadProcess?.close('terminated');
    else void uploadListing();
});
setInterval(() => { if (window.sv08Session?.elevated) void uploadListing(); }, 2000);
