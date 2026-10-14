/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Static image provenance: no controller calls and no administrator elevation. */
(() => {
    'use strict';
    const dialog = document.getElementById('project-source');
    const status = document.getElementById('source-status');
    let request = 0;
    async function load() {
        const current = ++request;
        status.textContent = 'Loading installed build information…';
        document.getElementById('source-downloads').replaceChildren();
        document.getElementById('source-public-help').textContent = 'Matching public source has not been qualified for this build.';
        try {
            const response = await fetch('project-source.json', {cache:'no-store', credentials:'same-origin'});
            if (!response.ok) throw Error('unavailable');
            const data = await response.json();
            if (current !== request) return;
            if (data.format_version !== 1 || !/^[a-f0-9]{64}$/.test(data.build_id || '')) throw Error('invalid');
            document.getElementById('source-revision').textContent = data.source_revision || 'Development snapshot';
            document.getElementById('source-build').textContent = data.build_id;
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
            if (current !== request) return;
            status.textContent = 'Installed source information unavailable. Check again or ask the image publisher for matching source.';
            document.getElementById('source-revision').textContent = 'Unavailable';
            document.getElementById('source-build').textContent = 'Unavailable';
        }
    }
    function open() { if (!dialog.open) dialog.showModal(); load(); }
    document.getElementById('source-open').addEventListener('click', open);
    document.getElementById('source-retry').addEventListener('click', load);
    if (location.hash === '#project-source') open();
})();
