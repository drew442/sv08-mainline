// SPDX-License-Identifier: AGPL-3.0-or-later
// Real SDK + adapter + Janus RTP/WebRTC playback; disposable loopback fixtures only.
import fs from 'node:fs';
import path from 'node:path';
import dgram from 'node:dgram';
import { spawn, execFileSync } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import assert from 'node:assert/strict';
const [execute, chrome, directory, destination, janusUrl, streamId, rtpPort] = process.argv.slice(2);
assert.equal(execute, '--execute');
const links = JSON.parse(execFileSync('ip', ['-j', '-d', 'link'], {encoding:'utf8'}));
assert.deepEqual(links.map(x => x.ifname).sort(), ['lo','sv08test0'], 'Isolated Janus fixture interfaces required');
assert.equal(links.find(x => x.ifname==='sv08test0').linkinfo?.info_kind,'dummy','Fixture must use a disposable dummy interface');
const addresses = JSON.parse(execFileSync('ip', ['-j', 'addr', 'show', 'dev', 'sv08test0'], {encoding:'utf8'}));
assert.deepEqual(addresses.flatMap(x => x.addr_info).filter(x=>x.family==='inet').map(x=>[x.local,x.prefixlen]),[['192.0.2.1',32]],'Exact documentation-only ICE address required');
for (const family of ['-4','-6']) {
    const routes = JSON.parse(execFileSync('ip', ['-j',family,'route','show','table','all'], {encoding:'utf8'}));
    assert(!routes.some(x=>x.dst==='default'),'No default route permitted');
    assert(routes.every(x=>!x.dev || ['lo','sv08test0'].includes(x.dev)),'No external route interfaces permitted');
}
const url = new URL(janusUrl);
assert(['ws:', 'http:'].includes(url.protocol) && url.hostname === '127.0.0.1');
assert(/^\d+$/.test(streamId) && /^\d+$/.test(rtpPort) && Number(rtpPort)>0 && Number(rtpPort)<65536);
const root = fs.realpathSync(directory), output = path.resolve(destination);
fs.mkdirSync(output); const profile = path.join(output,'profile');
// A minimal Vite config compiles the same production adapter, SDK and dependencies.
const config = path.join(output,'vite.config.mjs');
fs.writeFileSync(config, `export default {root:${JSON.stringify(root)},server:{host:'127.0.0.1',port:0},configFile:false};\n`);
const log = fs.openSync(path.join(output,'process.log'),'w');
const vite = spawn(process.execPath,[path.join(root,'node_modules/vite/bin/vite.js'),'--config',config],{detached:true,stdio:['ignore',log,log]});
let browser, socket, timer; const udp = dgram.createSocket('udp4'); const pending = new Map();
try {
    let origin;
    for (let i=0;i<100;i++) {
        const text = fs.readFileSync(path.join(output,'process.log'),'utf8');
        origin = text.match(/http:\/\/127\.0\.0\.1:\d+/)?.[0]; if (origin) break;
        if (vite.exitCode !== null) throw new Error('Vite exited: '+text); await delay(100);
    }
    assert(origin,'Vite readiness timeout');
    browser = spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-extensions','--disable-background-networking','--no-first-run','--no-default-browser-check','--autoplay-policy=no-user-gesture-required','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{detached:true,stdio:['ignore',log,log]});
    let port;
    for (let i=0;i<100;i++) {
        try { port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0]; break; } catch { await delay(100); }
    }
    assert(port,'Browser readiness timeout');
    const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket = new WebSocket(tabs.find(t => t.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject) => { socket.onopen=resolve; socket.onerror=reject; });
    let serial=0; const exceptions=[];
    function send(method,params={}) {
        return new Promise((resolve,reject) => {
            const id=++serial, timeout=setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout '+method)); },15000);
            pending.set(id,{resolve,reject,timeout}); socket.send(JSON.stringify({id,method,params}));
        });
    }
    socket.onmessage=({data}) => {
        const event=JSON.parse(data), waiter=pending.get(event.id);
        if (waiter) { clearTimeout(waiter.timeout); pending.delete(event.id); if (event.error) waiter.reject(new Error(JSON.stringify(event.error))); else waiter.resolve(event.result); }
        if (event.method==='Fetch.requestPaused') {
            const {requestId,request}=event.params;
            const allowed=request.url.startsWith(origin+'/') || request.url===janusUrl;
            send(allowed?'Fetch.continueRequest':'Fetch.failRequest',allowed?{requestId}:{requestId,errorReason:'BlockedByClient'}).catch(error=>exceptions.push(String(error)));
        }
        if (event.method==='Runtime.exceptionThrown') exceptions.push(event.params);
    };
    async function evaluate(expression) {
        const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
        if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
        return result.result.value;
    }
    await send('Runtime.enable'); await send('Page.enable');
    await send('Fetch.enable',{patterns:[{urlPattern:'*'}]});
    // Navigate to a Vite-served asset rather than starting the full Mainsail application.
    await send('Page.navigate',{url:origin+'/src/plugins/janusStream.ts'});
    await delay(300);
    const frame = await evaluate(`(async()=>{
        const chunks=[]; const encoder=new VideoEncoder({output:chunk=>{const bytes=new Uint8Array(chunk.byteLength);chunk.copyTo(bytes);chunks.push(Array.from(bytes))},error:error=>{throw error}});
        encoder.configure({codec:'vp8',width:320,height:240,bitrate:300000,framerate:10});
        const canvas=document.createElement('canvas');canvas.width=320;canvas.height=240;
        const ctx=canvas.getContext('2d');ctx.fillStyle='#1874cc';ctx.fillRect(0,0,320,240);ctx.fillStyle='#fff';ctx.fillRect(80,60,160,120);
        const frame=new VideoFrame(canvas,{timestamp:0});encoder.encode(frame,{keyFrame:true});frame.close();await encoder.flush();encoder.close();
        return chunks[0];
    })()`);
    assert(frame?.length,'WebCodecs produced no VP8 keyframe');
    const payload=Buffer.from(frame); let seq=1000, timestamp=100000, sent=0;
    function transmit() {
        for (let offset=0;offset<payload.length;offset+=1000) {
            const fragment=payload.subarray(offset,offset+1000), last=offset+1000>=payload.length;
            const packet=Buffer.alloc(13+fragment.length);packet[0]=0x80;packet[1]=100|(last?0x80:0);
            packet.writeUInt16BE(seq++ & 0xffff,2);packet.writeUInt32BE(timestamp>>>0,4);packet.writeUInt32BE(0x12345678,8);
            packet[12]=offset===0?0x10:0;fragment.copy(packet,13);udp.send(packet,Number(rtpPort),'127.0.0.1');sent++;
        }
        timestamp+=9000;
    }
    transmit();timer=setInterval(transmit,100);
    await evaluate(`(async()=>{
        const {JanusStream}=await import('/src/plugins/janusStream.ts');
        document.body.innerHTML=''; const video=document.createElement('video');video.autoplay=true;video.muted=true;video.playsInline=true;document.body.append(video);
        window.proof={video,status:[],player:new JanusStream(video,s=>window.proof.status.push(s))};
        window.proof.player.start({server:${JSON.stringify(janusUrl)},iceServers:[]},${Number(streamId)});
    })()`);
    async function playback(minFrames) {
        let state;
        for (let i=0;i<150;i++) {
            state=await evaluate(`(()=>{const p=window.proof;return {status:p.status,width:p.video.videoWidth,height:p.video.videoHeight,frames:p.video.getVideoPlaybackQuality().totalVideoFrames,attached:!!p.video.srcObject}})()`);
            if (state.width===320 && state.height===240 && state.frames>minFrames && state.status.at(-1)==='started') return state;
            await delay(100);
        }
        throw new Error('Playback timeout: '+JSON.stringify(state));
    }
    const first=await playback(2);
    await evaluate(`window.proof.player.stop()`);
    const stopped=await evaluate(`window.proof.video.srcObject===null`);assert(stopped,'stop retained video stream');
    await evaluate(`window.proof.player.start({server:${JSON.stringify(janusUrl)},iceServers:[]},${Number(streamId)})`);
    const second=await playback(first.frames+2);
    await evaluate(`window.proof.player.stop();window.proof.player.stop()`);
    assert.equal(await evaluate(`window.proof.video.srcObject===null`),true);
    assert.equal(exceptions.length,0,'Uncaught browser exceptions');
    const result={passed:true,actual_janus_webrtc_playback:true,first,second,stopped,rtp_packets:sent,encoded_keyframe_bytes:payload.length,uncaught_exceptions:exceptions,physical_hardware:false,production_component_mounted:false};
    fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2)+'\n'); console.log(result);
} finally {
    clearInterval(timer);for (const p of pending.values()) { clearTimeout(p.timeout);p.reject(new Error('Harness cleanup')); }pending.clear();
    socket?.close();try { udp.close(); } catch {}
    for (const child of [browser,vite]) if(child) { try { process.kill(-child.pid,'SIGTERM'); } catch {} }
    await Promise.all([browser,vite].filter(Boolean).map(child=>child.exitCode!==null?Promise.resolve():new Promise(resolve=>{const timeout=setTimeout(()=>{try{process.kill(-child.pid,'SIGKILL')}catch{}},2000);child.once('exit',()=>{clearTimeout(timeout);resolve()})})));
    fs.closeSync(log);
}
