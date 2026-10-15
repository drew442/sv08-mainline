// SPDX-License-Identifier: AGPL-3.0-or-later
// Run with pinned Node and a fresh build's node_modules. No network or browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const { EventEmitter } = require('node:events');
const modules = path.resolve(process.argv[2]);
const requireBuild = createRequire(path.join(modules, '__notice_regression__.cjs'));
const requestPath = requireBuild.resolve('request-progress');
const throttlePath = createRequire(requestPath).resolve('throttleit');
assert.equal(JSON.parse(fs.readFileSync(path.join(path.dirname(throttlePath), 'package.json'))).version, '2.1.0');
for (const removed of ['vue-template-compiler', 'de-indent', 'he']) {
    assert.equal(fs.existsSync(path.join(modules, removed)), false, removed + ' remains installed');
}

function fixture() {
    let now = 10000;
    let nextId = 0;
    const timers = new Map();
    const ActualDate = Date;
    class ClockDate extends ActualDate {
        constructor(...args) { super(...(args.length ? args : [now])); }
        static now() { return now; }
    }
    const globals = {
        Date: ClockDate,
        setTimeout(fn, wait) { const id = ++nextId; timers.set(id, { at: now + Math.max(0, wait), fn }); return id; },
        clearTimeout(id) { timers.delete(id); },
    };
    function advance(relative) {
        const target = 10000 + relative;
        assert.ok(target >= now);
        let iterations = 0;
        while (true) {
            const pending = [...timers].filter(([, value]) => value.at <= target)
                .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
            if (!pending) break;
            assert.ok(++iterations < 1000, 'timer loop');
            timers.delete(pending[0]); now = pending[1].at; pending[1].fn();
        }
        now = target;
    }
    function load(filename, require) {
        const module = { exports: {} };
        vm.runInNewContext(fs.readFileSync(filename, 'utf8'), { ...globals, module, exports: module.exports, require }, { filename, timeout: 1000 });
        return module.exports;
    }
    const throttle = load(throttlePath, name => { throw Error('Unexpected throttle dependency: ' + name); });
    const requestProgress = load(requestPath, name => { assert.equal(name, 'throttleit'); return throttle; });
    return { throttle, requestProgress, advance, time: () => now - 10000 };
}

for (const scenario of [
    { wait: 100, calls: [[0, 'first'], [25, 'a'], [50, 'last'], [125, 'later']], expected: [[0, 'first'], [100, 'last'], [200, 'later']] },
    { wait: 100, calls: [[0, 'a'], [100, 'b'], [200, 'c']], expected: [[0, 'a'], [100, 'b'], [200, 'c']] },
    { wait: 0, calls: [[0, 'a'], [1, 'b'], [2, 'c']], expected: [[0, 'a'], [1, 'b'], [2, 'c']] },
]) {
    const clock = fixture(); const actual = [];
    const receiver = { id: 'request-context' };
    const emit = clock.throttle(function (value) { assert.equal(this, receiver); actual.push([clock.time(), value]); }, scenario.wait);
    for (const [time, value] of scenario.calls) { clock.advance(time); emit.call(receiver, value); }
    clock.advance(500);
    assert.deepEqual(actual, scenario.expected);
}

// Exercise request-progress itself, including latest state and suppressed trailing
// callbacks after end. These are the actual supplier modules used by Cypress.
{
    const clock = fixture(); const request = new EventEmitter(); const response = new EventEmitter();
    response.headers = { 'content-length': '100' };
    const progress = [];
    request.on('progress', state => progress.push({ at: clock.time(), percent: state.percent, transferred: state.size.transferred }));
    assert.equal(clock.requestProgress(request, { throttle: 100 }), request);
    assert.equal(clock.requestProgress(request), request);
    request.emit('request'); request.emit('response', response); clock.advance(0);
    response.emit('data', Buffer.alloc(10));
    clock.advance(25); response.emit('data', Buffer.alloc(20));
    clock.advance(50); response.emit('data', Buffer.alloc(30));
    clock.advance(100);
    assert.deepEqual(progress, [{ at: 0, percent: 0.1, transferred: 10 }, { at: 100, percent: 0.6, transferred: 60 }]);
    clock.advance(125); response.emit('data', Buffer.alloc(40)); request.emit('end'); clock.advance(500);
    assert.equal(progress.length, 2); assert.equal(request.progressState, null); assert.equal(request.progressContext, null);
}

// Mainsail's pinned plugin-vue2 uses Vue's own SFC compiler, not the removed
// root vue-template-compiler declaration. Compile a real Vue2 template.
const compiler = requireBuild('vue/compiler-sfc');
const compiled = compiler.compileTemplate({ source: '<div>{{ value }}</div>', filename: 'notice-fixture.vue', id: 'notice-fixture' });
assert.deepEqual(compiled.errors, []);
assert.match(compiled.code, /value/);
console.log('Notice dependency API, request-progress and Vue2 compiler regressions passed');
