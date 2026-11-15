/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Fixed public documents, read through the ordinary authenticated file channel. */
(() => {
    'use strict';
    const dialog = document.getElementById('project-source');
    const status = document.getElementById('source-status');
    const documents = [
        ['source-license', 'project-LICENSE.txt'],
        ['source-notice', 'project-NOTICE.txt'],
        ['source-provenance', 'project-source.json'],
    ];
    let request = 0, documentURLs = [];
    function clearDocuments() {
        for (const url of documentURLs) URL.revokeObjectURL(url);
        documentURLs = [];
        for (const [id] of documents) {
            const link = document.getElementById(id);
            link.removeAttribute('href');link.setAttribute('aria-disabled', 'true');
        }
    }
    async function readDocument(name) {
        const file = cockpit.file('/usr/share/cockpit/sv08-host/' + name);
        try {
            const content = await file.read();
            if (typeof content !== 'string' || content.length > 2 * 1024 * 1024) throw Error('unavailable');
            return content;
        } finally { file.close(); }
    }
    function integrity(state, reason) {
        const styles = {
            checking: ['Checking', 'neutral', 'M12 8v4m0 4h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20'],
            intact: ['Intact', 'success', 'm6 12 4 4 8-8M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20'],
            tainted: ['Tainted', 'error', 'm8 8 8 8m0-8-8 8M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20'],
            unavailable: ['Unavailable', 'neutral', 'M12 8v4m0 4h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20'],
        };
        const [label, tone, path] = styles[state];
        document.getElementById('source-integrity').dataset.tone = tone;
        document.getElementById('source-integrity-label').textContent = label;
        document.getElementById('source-integrity-icon').setAttribute('d', path);
        document.getElementById('source-integrity-reason').textContent = reason;
    }
    async function verify() {
        const result = await sv08View('provenance');
        if (result.scope !== 'local-project-record' ||
            !['intact', 'tainted', 'unavailable'].includes(result.state) ||
            !['record-matches', 'record-mismatch', 'baseline-missing', 'read-failed'].includes(result.reason) ||
            (result.state === 'intact' && (result.reason !== 'record-matches' || !/^[a-f0-9]{64}$/.test(result.build_id || '')))) throw Error('unavailable');
        return result;
    }
    async function load() {
        const current = ++request;
        clearDocuments();
        integrity('checking', 'Checking installed project files…');
        document.getElementById('source-title').focus({preventScroll: true});
        dialog.scrollTop = 0;
        document.getElementById('source-revision').textContent = 'Checking…';
        document.getElementById('source-build').textContent = 'Checking…';
        status.textContent = 'Loading installed build information…';
        const feedback = document.getElementById('source-documents-status');
        feedback.hidden = true;
        document.getElementById('source-downloads').replaceChildren();
        document.getElementById('source-public-help').textContent = 'Matching public source has not been qualified for this build.';
        const results = await Promise.allSettled([...documents.map(([,name]) => readDocument(name)), verify()]);
        const reads = results.slice(0, 3);
        let displayedBuild = null;
        if (current !== request) return;
        for (let i=0;i<documents.length;i++) {
            if (reads[i].status !== 'fulfilled') continue;
            const link = document.getElementById(documents[i][0]);
            const url = URL.createObjectURL(new Blob([reads[i].value], {type:'text/plain;charset=utf-8'}));
            documentURLs.push(url);link.href=url;link.removeAttribute('aria-disabled');
        }
        if (reads.some(result => result.status !== 'fulfilled')) {
            feedback.hidden = false;
            feedback.textContent = 'Some project documents could not be read. Check your connection or sign in again, then choose Check again.';
        }
        try {
            if (reads[2].status !== 'fulfilled') throw Error('unavailable');
            const data = JSON.parse(reads[2].value);
            if (data.format_version !== 1 || !/^[a-f0-9]{64}$/.test(data.build_id || '')) throw Error('invalid');
            document.getElementById('source-revision').textContent = data.source_revision || 'Development snapshot';
            document.getElementById('source-build').textContent = data.build_id;
            displayedBuild = data.build_id;
            status.textContent = 'Project build recorded. Public source is unqualified.';
            const offer = data.public_source;
            if (data.development === false && offer?.qualified === true && offer.scope === 'project-source-only' &&
                offer.overall_release_qualified === false && offer.build_id === data.build_id &&
                offer.source_revision === data.source_revision && /^[a-f0-9]{40}$/.test(data.source_revision || '') && /^[a-f0-9]{64}$/.test(offer.archive?.sha256 || '')) {
                const url = new URL(offer.archive.url);
                const tokens = url.pathname.split(/[^a-zA-Z0-9]/);
                if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash ||
                    (!tokens.includes(data.source_revision) && !tokens.includes(offer.archive.sha256))) throw Error('invalid');
                const link = document.createElement('a');
                link.href = url.href; link.target = '_blank'; link.rel = 'noopener';
                link.textContent = 'Download matching project source';
                document.getElementById('source-downloads').append(link);
                status.textContent = 'Matching public project source checked for this build.';
                document.getElementById('source-public-help').textContent = 'The archive includes the recorded project source, patches and build/install inputs. This source check applies to the staged project build; it does not check later image changes.';
                return;
            }
            document.getElementById('source-public-help').textContent = 'Matching public source is unavailable or has not passed the required source qualification. Ask the image publisher for this exact build, its patches and build/install inputs.';
        } catch (_) {
            status.textContent = 'Installed source information unavailable. Check again or ask the image publisher for matching source.';
            document.getElementById('source-revision').textContent = 'Unavailable';
            document.getElementById('source-build').textContent = 'Unavailable';
        } finally {
            const verified = results[3];
            if (verified.status !== 'fulfilled') {
                integrity('unavailable', 'The check could not complete. Check your connection or sign in again, then choose Check again.');
            } else if (verified.value.state === 'intact' && displayedBuild === verified.value.build_id) {
                integrity('intact', 'Installed project files match the local build record.');
            } else if (verified.value.state === 'tainted' || (verified.value.state === 'intact' && displayedBuild !== null)) {
                integrity('tainted', 'Installed project files or build records differ. Ask the image publisher for a matching build.');
            } else {
                integrity('unavailable', 'The local build record could not be read. Choose Check again or ask the image publisher.');
            }
        }
    }
    function open() { if (!dialog.open) dialog.showModal(); load(); }
    document.getElementById('source-open').addEventListener('click', open);
    document.getElementById('source-retry').addEventListener('click', load);
    window.addEventListener('pagehide', () => { ++request;clearDocuments(); });
    if (location.hash === '#project-source') open();
})();
