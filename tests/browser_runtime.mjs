// Shared Node 22 / Chromium startup. Own only the fresh profile and child group.
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';

export function finiteStatusDiagnostic(area, error, secrets = []) {
    if (!['host','printer','network','software','identity','mainsail-access'].includes(area))
        throw Error('Unsupported finite status area');
    const sanitize = value => {
        let text = typeof value === 'string' ? value : '';
        for (const secret of secrets.filter(value => typeof value === 'string' && value.length))
            text = text.split(secret).join('[redacted]');
        return text.replace(/[\u0000-\u001f\u007f]/g, ' ').slice(0, 512);
    };
    return {area, method:'status', message:sanitize(error?.message), problem:sanitize(error?.problem),
        exit_status:Number.isInteger(error?.exit_status) ? error.exit_status : null,
        exit_signal:typeof error?.exit_signal === 'string' && /^[A-Z0-9_-]{1,40}$/.test(error.exit_signal)
            ? sanitize(error.exit_signal) : null};
}

export function startBrowser({chrome, output, scratch = process.env.SV08_BROWSER_PROFILE_ROOT
    || process.env.SV08_UI_SCRATCH || output, args = [], zoom = 1, timeoutMs = 10000}) {
    if (![1, 2].includes(zoom)) throw Error('Supported browser zoom: 1 or 2');
    // Use the assigned short directory when supplied. A path length is diagnostic,
    // not a claimed root cause for an earlier browser startup failure.
    fs.mkdirSync(output, {recursive:true, mode:0o700});
    const profile = fs.mkdtempSync(path.join(scratch, 'chrome-'));
    fs.chmodSync(profile, 0o700);
    fs.mkdirSync(path.join(profile, 'Default'), {mode:0o700});
    // Chromium stores defaults by storage-partition key. The default partition
    // has an empty relative path, encoded as 'x'; a scalar here is ignored.
    // Verified with installed Chrome145: physical1024x600 => CSS512x300/DPR2.
    // This is persisted browser zoom, not CSS zoom or CDP scaling.
    fs.writeFileSync(path.join(profile, 'Default', 'Preferences'), JSON.stringify({
        partition:{default_zoom_level:{x:Math.log(zoom) / Math.log(1.2)}, per_host_zoom_levels:{}}
    }), {mode:0o600});
    const logPath = path.join(output, 'browser.log');
    const log = fs.openSync(logPath, 'w', 0o600);
    const detached = process.env.SV08_UI_OWNED_PROCESS_GROUP !== '1';
    const command = ['--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--disable-background-networking', '--no-first-run', '--window-size=1024,600',
        '--disk-cache-size=1', '--media-cache-size=1', '--remote-debugging-port=0',
        '--user-data-dir='+profile, ...args, 'about:blank'];
    const child = spawn(chrome, command, {detached, stdio:['ignore', log, log]});
    const diagnosticPath = path.join(output, 'browser-startup.json');
    const diagnostic = {pid:child.pid ?? null, profile, profile_path_bytes:Buffer.byteLength(profile),
        stderr:logPath, timeout_ms:timeoutMs, browser_zoom:zoom, status:'starting', exit_code:null,
        signal:null, cleanup:'pending'};
    const persist = () => fs.writeFileSync(diagnosticPath, JSON.stringify(diagnostic, null, 2)+'\n', {mode:0o600});
    let spawnError, closed = false, stopped = false;
    child.on('error', error => {spawnError=error; diagnostic.spawn_error=error.message; persist();});
    const completion = new Promise(resolve => child.once('close', (code, signal) => {
        closed=true; diagnostic.exit_code=code; diagnostic.signal=signal; persist(); resolve();
    }));
    persist();
    const ready = (async () => {
        const started=Date.now();
        try {
            while (Date.now()-started < timeoutMs) {
                if (spawnError) throw spawnError;
                if (closed || child.exitCode !== null || child.signalCode !== null)
                    throw Error('Chromium exited before DevTools readiness');
                try {
                    const [port] = fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').split('\n');
                    if (/^[0-9]+$/.test(port) && Number(port)>0 && Number(port)<=65535) {
                        diagnostic.status='ready'; diagnostic.port=Number(port); persist(); return Number(port);
                    }
                } catch (error) {if (error.code !== 'ENOENT') throw error;}
                await delay(Math.min(50, timeoutMs));
            }
            throw Error('Chromium DevTools startup timeout; process handle retained until owned cleanup');
        } catch (error) {
            diagnostic.status='failed'; diagnostic.error=error.message; diagnostic.elapsed_ms=Date.now()-started; persist();
            throw Error(error.message+'; inspect '+diagnosticPath+' and '+logPath);
        }
    })();
    async function stop() {
        if (stopped) return;
        function signal(value) {
            try {if (detached && child.pid) process.kill(-child.pid, value); else child.kill(value);}
            catch (error) {if (error.code !== 'ESRCH') throw error;}
        }
        // Signal the owned group even if its leader exited; descendants can remain.
        signal('SIGTERM');
        if (!closed) await Promise.race([completion, delay(500)]);
        signal('SIGKILL');
        if (!closed) await Promise.race([completion, delay(2000)]);
        if (!closed) {diagnostic.cleanup='failed'; persist(); throw Error('Owned browser did not exit: '+child.pid);}
        fs.closeSync(log);
        fs.rmSync(profile, {recursive:true, force:true, maxRetries:5, retryDelay:100});
        stopped=true; diagnostic.cleanup='complete'; persist();
    }
    return {child, profile, ready, stop, diagnosticPath};
}

export async function assertBrowserZoom({send, evaluate, zoom = 2}) {
    // Set physical viewport only. Browser zoom itself must halve the CSS viewport
    // and multiply DPR; pinch/page scale and CSS zoom cannot satisfy this pair.
    await send('Emulation.setDeviceMetricsOverride', {width:1024, height:600, deviceScaleFactor:1, mobile:false});
    const metrics = await evaluate('({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,cssZoom:getComputedStyle(document.body).zoom,scale:visualViewport.scale,overflow:document.documentElement.scrollWidth>innerWidth})');
    if (Math.abs(metrics.width-1024/zoom)>1 || Math.abs(metrics.height-600/zoom)>1
        || Math.abs(metrics.dpr-zoom)>0.01 || !['1','normal'].includes(metrics.cssZoom)
        || Math.abs(metrics.scale-1)>0.01 || metrics.overflow)
        throw Error('Actual browser zoom/reflow assertion failed: '+JSON.stringify(metrics));
    return {...metrics, mechanism:'Chromium profile partition.default_zoom_level.x', zoom};
}
