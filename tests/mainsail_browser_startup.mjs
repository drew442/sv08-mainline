// Offline static startup only. No printer/API fixture or production activation.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { spawn, execFileSync } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import assert from 'node:assert/strict';
const [execute, chrome, directory, destination, apiPort] = process.argv.slice(2);
assert.equal(execute, '--execute', 'Requires --execute, browser, built dist and fresh output directory');
if (apiPort) {
    assert(/^[0-9]+$/.test(apiPort) && Number(apiPort)>0 && Number(apiPort)<65536);
    assert.deepEqual(JSON.parse(execFileSync('ip',['-j','link'],{encoding:'utf8'})).map(link=>link.ifname), ['lo'], 'API fixture requires loopback-only namespace');
}
const root = fs.realpathSync(directory), output = path.resolve(destination);
fs.mkdirSync(output);
const profile = path.join(output, 'profile');
const mime = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.woff2':'font/woff2'};
const server = http.createServer((req, res) => {
    const name = path.resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://localhost').pathname));
    if (name !== root && !name.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    if (apiPort && req.url === '/config.json') {
        res.setHeader('Content-Type','application/json');
        res.end(JSON.stringify({defaultLocale:'en',defaultMode:'dark',hostname:'127.0.0.1',port:Number(apiPort),instancesDB:'moonraker',instances:[]})); return;
    }
    const file = name === root ? path.join(root, 'index.html') : name;
    try { const data = fs.readFileSync(file); res.setHeader('Content-Type', mime[path.extname(file)] ?? 'application/octet-stream'); res.end(data); }
    catch { res.writeHead(404).end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const log = fs.openSync(path.join(output, 'browser.log'), 'w');
const child = spawn(chrome, ['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-extensions','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'], { detached:true, stdio:['ignore',log,log] });
let socket;
try {
    let port;
    for (let i=0; i<100; i++) {
        try { port = fs.readFileSync(path.join(profile, 'DevToolsActivePort'),'utf8').split('\n')[0]; break; } catch { await delay(100); }
    }
    assert(port, 'Browser did not expose its test debugging endpoint');
    const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl);
    await new Promise((resolve,reject) => { socket.onopen=resolve; socket.onerror=reject; });
    let id=0;
    const pending = new Map(), exceptions=[];
    function send(method, params={}) {
        return new Promise((resolve,reject) => {
            const request=++id;
            const timer=setTimeout(() => { pending.delete(request); reject(new Error('CDP timeout: '+method)); },5000);
            pending.set(request, {resolve,reject,timer}); socket.send(JSON.stringify({id:request,method,params}));
        });
    }
    socket.onmessage = ({data}) => {
        const event=JSON.parse(data);
        if (event.id && pending.has(event.id)) {
            const p=pending.get(event.id); pending.delete(event.id); clearTimeout(p.timer);
            if (event.error) p.reject(new Error(JSON.stringify(event.error))); else p.resolve(event.result);
        }
        if (event.method === 'Runtime.exceptionThrown') exceptions.push(event.params);
        if (event.method === 'Fetch.requestPaused') {
            const {requestId,request}=event.params;
            const method=(request.url.startsWith(origin+'/') || (apiPort && request.url.startsWith(`http://127.0.0.1:${apiPort}/`))) ? 'Fetch.continueRequest' : 'Fetch.failRequest';
            send(method, method.endsWith('failRequest') ? {requestId,errorReason:'BlockedByClient'} : {requestId}).catch(error => exceptions.push(String(error)));
        }
    };
    await send('Runtime.enable'); await send('Page.enable');
    await send('Fetch.enable',{patterns:[{urlPattern:'*'}]});
    await send('Page.navigate',{url:origin+'/'});
    let mounted=false;
    for (let i=0;i<100;i++) {
        const result=await send('Runtime.evaluate',{expression:'Boolean(document.querySelector("[data-app=true]"))',returnByValue:true});
        if (result.result.value) { mounted=true; break; } await delay(100);
    }
    assert(mounted,'Vue application did not mount'); await delay(1000);
    let apiState=null;
    if (apiPort) {
        for (let i=0;i<300;i++) {
            const response=await send('Runtime.evaluate',{expression:'JSON.stringify((() => { const s=document.querySelector("[data-app=true]").__vue__.$store.state; return {connected:s.socket.isConnected,version:s.server.moonraker_version,klippy:s.server.klippy_state,initializing:s.socket.initializationList}; })())',returnByValue:true});
            if (response.result.value) apiState=JSON.parse(response.result.value);
            if (apiState?.connected && apiState.version && apiState.klippy==='disconnected' && apiState.initializing.length===0) break;
            await delay(100);
        }
        assert(apiState?.connected && apiState.version && apiState.klippy==='disconnected' && apiState.initializing.length===0,'API fixture did not initialize: '+JSON.stringify(apiState));
    }
    let fileRoundtrip=false;
    if (apiPort) {
        const proof=await send('Runtime.evaluate',{awaitPromise:true,returnByValue:true,
            expression:`(async () => {
                const base='http://127.0.0.1:${apiPort}', name='sv08-browser-proof.cfg';
                const form=new FormData(); form.append('root','config');
                form.append('file',new Blob(['# browser API fixture\\n']),name);
                const upload=await fetch(base+'/server/files/upload',{method:'POST',body:form});
                if (!upload.ok) throw new Error('Upload failed: '+upload.status);
                const read=await fetch(base+'/server/files/config/'+name);
                const text=await read.text();
                const removed=await fetch(base+'/server/files/config/'+name,{method:'DELETE'});
                return read.ok && text==='# browser API fixture\\n' && removed.ok;
            })()`});
        assert.equal(proof.result.value,true,'Browser configuration file roundtrip failed'); fileRoundtrip=true;
    }
    const dom=await send('Runtime.evaluate',{expression:'document.documentElement.outerHTML',returnByValue:true});
    fs.writeFileSync(path.join(output,'dom.html'),dom.result.value);
    const screenshot=await send('Page.captureScreenshot',{format:'png'});
    fs.writeFileSync(path.join(output,'startup.png'),Buffer.from(screenshot.data,'base64'));
    fs.writeFileSync(path.join(output,'exceptions.json'),JSON.stringify(exceptions,null,2)+'\n');
    assert.equal(exceptions.length,0,'Uncaught browser exceptions');
    const result={passed:true,static_application_mounted:true,uncaught_exceptions:0,physical_hardware:false,moonraker_connected:Boolean(apiPort),api_state:apiState,configuration_file_roundtrip:fileRoundtrip,full_workload_validation:false};
    fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2)+'\n'); console.log(result);
} finally {
    socket?.close();
    try { process.kill(-child.pid,'SIGTERM'); } catch {}
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); fs.closeSync(log);
}
