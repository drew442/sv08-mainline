import vm from 'node:vm';
import fs from 'node:fs';
import assert from 'node:assert/strict';

// A small DOM for navigation's actual dependencies. Mutation records are queued
// and delivered at explicit microtask checkpoints, including observer mutations.
const observers=[];
function changed(target,addedNodes=[],removedNodes=[]){
 for(const observer of observers){
  if(!observer.options.childList)continue;
  if(target===observer.target || observer.options.subtree && observer.target.contains(target))observer.records.push({type:'childList',target,addedNodes,removedNodes});
 }
}
class MutationObserver {
 constructor(callback){this.callback=callback;this.records=[];observers.push(this);}
 observe(target,options){this.target=target;this.options=options;}
}
function checkpoint(){
 for(let deliveries=0;deliveries<20;deliveries++){
  const pending=observers.filter(o=>o.records.length);
  if(!pending.length)return;
  for(const observer of pending){const records=observer.records.splice(0);observer.callback(records,observer);}
 }
 assert.fail('Icon decoration did not settle after mutation delivery');
}
const names=['overview','images','software','settings','recovery','printer','network','mainsail-access','identity','printer-connections','definition-sources','definitions'];
const listeners={},docListeners={},events=[],timers=[];let focused='';
function element(id='',tagName='DIV'){
 const classes=new Set();
 return {id,tagName,dataset:{},attrs:{},hidden:false,children:[],parentElement:null,
  classList:{add(...names){names.forEach(n=>classes.add(n));},remove(n){classes.delete(n);},contains(n){return classes.has(n);},toggle(n,on=!classes.has(n)){on?classes.add(n):classes.delete(n);return on;}},
  setAttribute(k,v){this.attrs[k]=v;},getAttribute(k){return this.attrs[k];},removeAttribute(k){delete this.attrs[k];},
  addEventListener(n,f){this.listeners??={};this.listeners[n]=f;},focus(){focused=this.id;},
  contains(e){return this===e||this.children.some(child=>child.contains(e));},
  closest(selector){return selector.startsWith('#')?(this.id===selector.slice(1)?this:this.parentElement?.closest(selector)??null):null;},
  querySelector(selector){if(selector===':scope > svg')return this.children.find(e=>e.tagName==='svg')??null;return null;},
  replaceChildren(){const removed=this.children;this.children=[];removed.forEach(e=>e.parentElement=null);changed(this,[],removed);},
  append(e){this.children.push(e);e.parentElement=this;changed(this,[e]);},
  prepend(e){this.children.unshift(e);e.parentElement=this;changed(this,[e]);}
 };
}
const pages=names.map(name=>element(name));
const buttons=['overview','printer','images','network','mainsail-access','settings'].map(name=>Object.assign(element(name+'-nav','BUTTON'),{dataset:{page:name}}));
const notice=element('notice'),jobs=element('image-history'),context=element('task-context'),main=element('main'),menu=element('navigation-toggle'),nav=element('task-navigation');menu.attrs['aria-expanded']='false';
main.append(context);pages.forEach(p=>main.append(p));
const dynamicLabels=[];
nav.querySelectorAll=()=>buttons;nav.querySelector=()=>buttons.find(b=>b.attrs['aria-current']);
const location={hash:'#printer'},history={replaceState(a,b,url){location.hash=url;},pushState(a,b,url){location.hash=url;}};
const heading=element('hardware-heading','H1');
const document={addEventListener(n,f){docListeners[n]=f;},createElement(tag){return element('',tag.toUpperCase());},createElementNS(namespaceURI,tag){return Object.assign(element('',tag),{namespaceURI});},
 querySelector(selector){return selector==='#printer h1'?heading:null;},
 getElementById(id){return {main,notice,'task-context':context,'task-navigation':nav,'navigation-toggle':menu,'jobs-summary':{closest(){return jobs;}}}[id]??pages.find(p=>p.id===id);},
 querySelectorAll(selector){
  if(selector==='dialog')return [];
  if(selector==='main > .page')return pages;
  if(selector==='[data-host-status]')return [notice,jobs];
  if(selector.startsWith('.metrics article'))return dynamicLabels;
  if(selector.startsWith('[data-page]'))return [...buttons,...context.children];
  throw Error('Unimplemented navigation selector: '+selector);
 }
};
// Browser window properties are also global identifiers (sv08Presentation).
const browser={document,location,history,MutationObserver,setTimeout(callback){timers.push(callback);},CustomEvent:class{constructor(type,init){this.type=type;this.detail=init.detail;}},addEventListener(n,f){listeners[n]=f;},dispatchEvent(e){events.push(e);}};
browser.window=browser;
vm.runInNewContext(fs.readFileSync(new URL('../ui/host/navigation.js',import.meta.url),'utf8'),browser);
checkpoint();
assert.equal(observers.length,1);assert.equal(observers[0].target,main);assert.equal(observers[0].options.subtree,true);
assert(!pages.find(p=>p.id==='printer').hidden);assert(notice.hidden);assert(jobs.hidden);assert.equal(context.children.length,4);
const icon=e=>e.children.filter(c=>c.tagName==='svg');
for(const button of [...buttons,...context.children]){
 assert.equal(icon(button).length,1);assert.equal(icon(button)[0].attrs['aria-hidden'],'true');assert.equal(icon(button)[0].attrs.focusable,'false');assert(icon(button)[0].children[0].attrs.d);
}
const label=element('selected-part');label.classList.add('printer-selected-definition');
dynamicLabels.push(label,heading);main.append(label);main.append(heading);
assert.equal(icon(label).length,0,'Dynamic labels wait for mutation delivery');checkpoint();
assert.equal(icon(label).length,1,'Observed dynamic object receives an icon');assert.equal(icon(heading).length,0,'Headings stay plain');
label.append(element('extra-content'));checkpoint();assert.equal(icon(label).length,1,'Repeated mutation does not duplicate icons');
browser.sv08Navigation.go('identity');checkpoint();assert(!pages.find(p=>p.id==='identity').hidden);assert.equal(buttons.find(b=>b.dataset.page==='mainsail-access').attrs['aria-current'],'page');
browser.sv08Navigation.go('settings');checkpoint();assert.equal(focused,'main');assert(!notice.hidden);assert(jobs.hidden);
browser.sv08Navigation.go('updates');checkpoint();assert.equal(location.hash,'#images');assert(!jobs.hidden);
location.hash='#printer-connections';listeners.popstate();timers.splice(0).forEach(f=>f());checkpoint();assert.equal(buttons.find(b=>b.dataset.page==='printer').attrs['aria-current'],'page');
menu.listeners.click();assert.equal(menu.attrs['aria-expanded'],'true');assert.equal(focused,'printer-nav');docListeners.keydown({key:'Escape',preventDefault(){}});assert.equal(menu.attrs['aria-expanded'],'false');assert.equal(focused,'navigation-toggle');
context.children[0].onclick();checkpoint();assert.equal(location.hash,'#printer');assert.equal(focused,'hardware-heading');
location.hash='#unknown';listeners.hashchange();checkpoint();assert.equal(location.hash,'#overview');assert.equal(events.at(-1).detail.to,'overview');
console.log('Task routes, contextual history, status ownership, menu/heading focus and observed idempotent icons PASS');
