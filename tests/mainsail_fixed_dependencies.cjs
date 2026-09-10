// Run with the pinned Node binary and an isolated build's node_modules path.
// Bounded regressions for the selected upstream fixes; no browser/hardware claim.
const assert = require('node:assert/strict');
const path = require('node:path');
const modules = path.resolve(process.argv[2]);
const yaml = require(path.join(modules, 'js-yaml'));
const { customAlphabet, customRandom } = require(path.join(modules, 'nanoid'));
assert.equal(customAlphabet('ab', 0)(), '');
assert.equal(customRandom('ab', 0, size => new Uint8Array(size))(), '');
assert.throws(() => yaml.load('a: &a [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}]\nb: {<<: *a}',
    { schema: yaml.YAML11_SCHEMA, maxTotalMergeKeys: 10 }), /maxTotalMergeKeys/);
assert.equal(yaml.load('value: 42').value, 42);
console.log('Fixed dependency regression checks passed');
