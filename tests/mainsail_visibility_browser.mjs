// SPDX-License-Identifier: AGPL-3.0-or-later
// Shared original/candidate black-box fixture. Never starts the application.
import fs from 'node:fs';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import assert from 'node:assert/strict';
const [execute, chrome, directory, destination, mode] = process.argv.slice(2);
assert.equal(execute, '--execute');
assert(['baseline','candidate'].includes(mode));
const links = JSON.parse(execFileSync('ip', ['-j', 'link'], {encoding:'utf8'}));
assert.deepEqual(links.map(x=>x.ifname), ['lo'], 'Only loopback permitted; run in isolated network namespace');
for (const family of ['-4','-6']) {
    const routes=JSON.parse(execFileSync('ip',['-j',family,'route','show','table','all'],{encoding:'utf8'}));
    assert(routes.every(x=>!x.dev || x.dev==='lo'), 'External routes forbidden');
}
if (mode==='candidate') assert(process.env.VISIBILITY_BASELINE, 'VISIBILITY_BASELINE must name original result.json');
const root = fs.realpathSync(directory), output = path.resolve(destination);
fs.mkdirSync(output); const profile = path.join(output,'profile');
// A minimal Vite config serves the selected directive and real Vue runtime only.
const config = path.join(output,'vite.config.mjs');
const fixtureModule = `export {default as Vue} from 'vue'; export {ObserveVisibility} from ${JSON.stringify(mode==='baseline'?'vue-observe-visibility':'/src/plugins/observeVisibility.ts')};`;
const fixturePath = '/visibility-fixture.html';
const blankPage = '<!doctype html><html data-visibility-fixture="true"><head><meta charset="utf-8"><title>Visibility fixture</title></head><body></body></html>';
fs.writeFileSync(config, `export default {
    root:${JSON.stringify(root)},cacheDir:${JSON.stringify(path.join(output,'vite-cache'))},
    server:{host:'127.0.0.1',port:0},configFile:false,
    define:{'process.env.NODE_ENV':'"development"'},
    optimizeDeps:{entries:[],noDiscovery:true,include:${JSON.stringify(mode==='baseline'?['vue','vue-observe-visibility']:['vue'])}},
    plugins:[{name:'visibility-fixture',
        configureServer(server){server.middlewares.use((request,response,next)=>{
            if(request.url!==${JSON.stringify(fixturePath)})return next();
            response.statusCode=200;response.setHeader('Content-Type','text/html; charset=utf-8');
            response.end(${JSON.stringify(blankPage)});
        })},
        resolveId(id){if(id==='/@visibility-fixture')return '\\0visibility-fixture'},load(id){if(id==='\\0visibility-fixture')return ${JSON.stringify(fixtureModule)}}
    }]
};\n`);
const log = fs.openSync(path.join(output,'process.log'),'w');
const vite = spawn(process.execPath,[path.join(root,'node_modules/vite/bin/vite.js'),'--config',config],{detached:true,stdio:['ignore',log,log]});
let browser, socket; const pending = new Map();
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
    let serial=0; const exceptions=[], requests=[], navigations=[], forbiddenRequests=[];
    const fixtureUrl=origin+fixturePath;
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
            const {requestId,request,resourceType}=event.params;
            const pathname=new URL(request.url).pathname;
            requests.push({url:request.url,resourceType});
            const applicationRequest=pathname.endsWith('/src/main.ts') || pathname.endsWith('/App.vue') || pathname.endsWith('/index.html');
            const unexpectedDocument=resourceType==='Document' && request.url!==fixtureUrl;
            if(applicationRequest || unexpectedDocument)forbiddenRequests.push(request.url);
            const allowed=request.url.startsWith(origin+'/') && !applicationRequest && !unexpectedDocument;
            send(allowed?'Fetch.continueRequest':'Fetch.failRequest',allowed?{requestId}:{requestId,errorReason:'BlockedByClient'}).catch(error=>exceptions.push(String(error)));
        }
        if (event.method==='Page.frameNavigated' && !event.params.frame.parentId) navigations.push(event.params.frame.url);
        if (event.method==='Page.navigatedWithinDocument') navigations.push(event.params.url);
        if (event.method==='Runtime.exceptionThrown') exceptions.push(event.params);
    };
    async function evaluate(expression) {
        const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
        if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
        return result.result.value;
    }
    await send('Runtime.enable'); await send('Page.enable');
    await send('Fetch.enable',{patterns:[{urlPattern:'*'}]});
    await send('Emulation.setDeviceMetricsOverride',{width:800,height:600,deviceScaleFactor:1,mobile:false});
    await send('Page.navigate',{url:fixtureUrl});
    await delay(300);
    assert.equal(await evaluate(`document.documentElement.dataset.visibilityFixture==='true' && location.href===${JSON.stringify(fixtureUrl)} && document.scripts.length===0`),true,'Minimal script-free fixture page required');
    const observed=await evaluate(`(async()=>{
        const {Vue,ObserveVisibility}=await import('/@visibility-fixture');
        Vue.config.productionTip=false;
        Vue.directive('observe-visibility',ObserveVisibility);
        document.body.innerHTML='';document.body.style.margin='0';document.body.style.overflow='hidden';
        const pause=()=>new Promise(resolve=>setTimeout(resolve,130));
        const trace={};let active;
        async function stage(name, action=()=>{}) {
            await action();await Vue.nextTick();await pause();
            trace[name]={calls:active.calls.map(x=>[...x]),effects:{...active.effects},preview:!!document.querySelector('[data-preview]'),focused:document.activeElement?.dataset.focus==='yes'};
        }
        function mount({top=20,left=20,width=100,height=100,component=false,clip=false,scroll=false,emptyImage=false}={}) {
            const host=document.createElement('div');document.body.append(host);
            const Root={render(h){return h('div',this.$slots.default)}};
            const vm=new Vue({
                mounted(){this.ready=true},
                data:()=>({ready:false,top,left,width,height,shown:true,exists:true,tick:0,alternate:false,documentVisible:true,visible:false,calls:[],effects:{focus:0,preview:0,requests:0,chart:0,hls:0,temperature:0}}),
                methods:{
                    changed(value){this.calls.push(['first',value]);this.consume(value)},
                    swapped(value){this.calls.push(['second',value]);this.consume(value)},
                    consume(value){if(!this.ready)throw new Error('Callback before consumer initialization');this.visible=value;if(value){this.$refs.focus?.focus();this.effects.focus++;this.effects.chart++;this.effects.hls++;this.effects.preview++}if(value&&this.documentVisible)this.effects.requests++},
                    temperature(){if(this.visible)this.effects.temperature++}
                },
                render(h){
                    const target=this.exists?h(emptyImage?'img':component?Root:'div',{
                        key:'target',directives:[{name:'observe-visibility',value:this.alternate?this.swapped:this.changed}],
                        style:{position:'absolute',top:this.top+'px',left:this.left+'px',width:this.width+'px',height:this.height+'px',display:this.shown?'block':'none'},
                        attrs:emptyImage?{}:{'data-target':'yes'}
                    },emptyImage?[]:[h('input',{ref:'focus',attrs:{'data-focus':'yes'}})]):null;
                    return h('div',[h('span',[String(this.tick)]),clip||scroll?h('div',{ref:'clip',style:{position:'absolute',top:'0',left:'0',width:'150px',height:'150px',overflow:scroll?'auto':'hidden'}},[scroll?h('div',{style:{height:'1000px',position:'relative'}},[target]):target]):target,this.visible?h('div',{attrs:{'data-preview':'yes'}},['preview']):null])
                }
            }).$mount(host);
            active=vm;return vm;
        }
        async function dispose(vm){vm.$destroy();vm.$el.remove();await pause()}
        let vm=mount();await stage('visible-initial');
        await stage('unrelated-updates',()=>{vm.tick++;vm.temperature()});
        await stage('hidden',()=>{vm.top=700});
        await stage('hidden-unrelated',()=>{vm.tick++;vm.temperature()});
        await stage('partial',()=>{vm.top=550});
        await stage('edge',()=>{vm.top=600});
        await stage('outside-edge',()=>{vm.top=601});
        await stage('edge-return',()=>{vm.top=600});
        await stage('zero-visible',()=>{vm.top=20;vm.width=0;vm.height=0});
        await stage('zero-hidden',()=>{vm.top=700});
        await stage('restore',()=>{vm.top=20;vm.width=100;vm.height=100});
        await stage('display-none',()=>{vm.shown=false});
        await stage('display-return',()=>{vm.shown=true});
        await stage('callback-replaced',()=>{vm.alternate=true});
        await stage('callback-replaced-hidden',()=>{vm.top=700});
        await stage('callback-replaced-return',()=>{vm.top=20});
        await stage('document-hidden',()=>{vm.documentVisible=false;vm.top=700});
        await stage('document-hidden-visible-target',()=>{vm.top=20});
        await stage('removed',()=>{vm.exists=false});await dispose(vm);
        vm=mount({top:700});await stage('hidden-initial');await dispose(vm);
        vm=mount({clip:true,top:170});await stage('nested-clipped');
        await stage('nested-partial',()=>{vm.top=140});await dispose(vm);
        vm=mount({scroll:true,top:700});await stage('scroll-hidden');
        await stage('scroll-visible',()=>{vm.$refs.clip.scrollTop=650});await dispose(vm);
        vm=mount({component:true});await stage('component-root');await dispose(vm);
        vm=mount({emptyImage:true});await stage('empty-image');
        await stage('empty-image-hidden',()=>{vm.top=700});await dispose(vm);
        vm=mount();vm.$destroy();vm.$el.remove();await stage('unbind-before-initial');
        for(let i=0;i<3;i++){vm=mount();await stage('repeated-mount-'+i);await dispose(vm)}
        const first=mount();await pause();const second=mount({top:700});await pause();
        trace.independent={first:first.calls,second:second.calls};second.top=20;await Vue.nextTick();await pause();
        trace['independent-transition']={first:first.calls.map(x=>[...x]),second:second.calls.map(x=>[...x])};await dispose(first);await dispose(second);
        return {trace,vue:Vue.version};
    })()`);
    const {trace,vue}=observed;
    assert.deepEqual(forbiddenRequests,[],'Application bootstrap requests forbidden');
    assert.deepEqual(navigations,[fixtureUrl],'Unexpected browser navigation or reload');
    assert.equal(vue,'2.7.16','Real pinned Vue runtime required');
    assert.equal(exceptions.length,0,'Uncaught browser exceptions');
    // Candidate comparisons use exactly the observations saved before implementation.
    if(mode==='candidate') {
        const baseline=JSON.parse(fs.readFileSync(process.env.VISIBILITY_BASELINE,'utf8'));
        assert.equal(baseline.mode,'baseline');
        assert.deepEqual(trace,baseline.trace,'Native directive differs from original black-box behavior');
    }
    const result={passed:true,mode,vue,viewport:[800,600],trace,requests,navigations,uncaught_exceptions:exceptions,physical_hardware:false,production_components_mounted:false};
    fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
} finally {
    for (const p of pending.values()) { clearTimeout(p.timeout);p.reject(new Error('Harness cleanup')); }pending.clear();
    socket?.close();
    for (const child of [browser,vite]) if(child) { try { process.kill(-child.pid,'SIGTERM'); } catch {} }
    await Promise.all([browser,vite].filter(Boolean).map(child=>child.exitCode!==null?Promise.resolve():new Promise(resolve=>{const timeout=setTimeout(()=>{try{process.kill(-child.pid,'SIGKILL')}catch{}},2000);child.once('exit',()=>{clearTimeout(timeout);resolve()})})));
    fs.closeSync(log);
}
