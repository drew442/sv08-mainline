# Stable Workbox precache ordering

Target: Mainsail `32f99e1cf97640b23a52829dfa3a0aceee11d382`.
Two independent archive/npm/Vite builds produced identical files except sw.js:
the same font/image entries occurred in different order. The packages therefore
had different hashes despite matching assets. `0001-stable-precache-order.patch`
uses Workbox's supported manifestTransforms configuration to sort entries by URL
before service-worker generation. It also disables duplicate includeAssets/icon
collection because those entries are appended after the transform and introduced
a second source of unstable ordering; the existing glob covers the same files. It changes build configuration, not dependency
versions or application behavior. The profile hashes the patch; it is applied to
build archives only. The upstream checkout remains unchanged.

Validation: two fresh full builds plus comparison of precache URL/revision maps
against the unpatched artifact. Equal entries prove the transform did not omit
assets; equal package hashes test the original nondeterminism. The build result
records the actual outcome. This does not imply reproducibility across different
Node/npm/platform toolchains.

The patch follows the upstream source license. Upstreaming plan: propose stable
precache ordering to Mainsail or the PWA plugin with the two-build reproduction.
No upstream message has been sent. Retire when the selected upstream build emits
a deterministic precache list without this configuration.

## Fixed js-yaml and nanoid versions

`0002-pin-fixed-yaml-nanoid.patch` uses npm overrides and exact lockfile integrity
records for js-yaml 4.3.2 and nanoid 3.3.18. The source gitlink stays pinned;
the builder checks both the original and patched lock hashes. Only these two
package records change. npm's unrelated removal of libc metadata was excluded
from the reviewed patch. Install scripts remain disabled.

Primary fix provenance, accessed 2026-09-10:
[js-yaml maintainer advisory](https://github.com/nodeca/js-yaml/security/advisories/GHSA-2883-xcg3-v3hh)
and [Nano ID 3.3.18 release](https://github.com/ai/nanoid/releases/tag/3.3.18).
The [bounded regression](../../tests/mainsail_fixed_dependencies.cjs) checks zero-size
custom generators and enforcement of the YAML empty-merge limit. Use the pinned
Node executable with the isolated build's node_modules path and an external
five-second process timeout. Complete clean builds provide integration evidence.

Upstreaming/retirement: offer the lock updates to Mainsail when appropriate; no
message has been sent. Remove the override patch when the selected upstream lock
contains fixed compatible versions. This patch does not resolve the separate
Vue/Vuetify/ECharts and tooling audit findings.

## Notice-bearing throttle and removal of an unused compiler edge

`0003-notice-dependency-closure.patch` follows the first two patches against the
same upstream source revision. It uses npm's supported scoped override
`request-progress: { throttleit: "2.1.0" }`. The selected supplier tarball is
`https://registry.npmjs.org/throttleit/-/throttleit-2.1.0.tgz`, with exact SRI in
the patched lock. Its original `package/license` contains the author's full MIT
notice; no upstream license, copyright or archive bytes are changed.
`request-progress` retains its actual declared `throttleit: ^1.0.0` metadata.
The override selects the newer release explicitly, with its Node >=18 requirement
satisfied by the unchanged Node 22.23.2 pin. Cypress/request-progress remains
installed and keeps its functionality.

The root development `vue-template-compiler` declaration has no JavaScript,
TypeScript or Vue callsite in the pinned Mainsail source. The selected
`@pedrolamas/plugin-vue2` uses `vue/compiler-sfc`, supplied by the existing Vue
package. Removing that unused root declaration removes only its otherwise unused
`de-indent` and `he` children. The actual SFC compiler, Vue, Vue runtime features,
application imports and upstream tests remain selected.

Generate a lock only in a disposable source archive after patches 1 and 2, using
the pinned Node/npm and `npm install --package-lock-only --ignore-scripts
--no-audit --no-fund` with a unique task cache and separate empty user/global npm
configuration files. npm removed unrelated `libc` fields while rewriting the
lock; these unchanged supplier records and their original key order were retained
verbatim, as with patch 2. The final patch changes only the root development edge
and the throttleit record, and removes the three records listed above. It does
not change any other supplier metadata, application source, existing fixes or
precache configuration. The profile pins the complete patched lock and all three
patches; package revision 5 distinguishes the resulting artifact.

Validation uses [offline patch and lock checks](../../tests/test_mainsail_notice_dependencies.py)
and [runtime dependency regressions](../../tests/mainsail_notice_dependencies.cjs).
The Python checks apply every patch with zero fuzz and verify pins, the exact
manifest/lock delta, unchanged supplier declarations and absent compiler callsites.
After a fresh package build, run the CJS check with the pinned Node binary and
that build's `source/node_modules` directory under a five-second process timeout.
It exercises leading/trailing throttling, callback arguments/receiver, actual
request-progress state and end cleanup, and a real Vue2 SFC template compilation.
Two coordinator-owned clean builds remain necessary integration and repeatability
evidence; source checks alone do not establish them.

Original licensing facts remain separate. `resolve_npm_notices.py
--selection-inputs INPUTS --output REPORT` accounts for all 69 historical records
against a pinned selected lock, the retained supplemental notices and exact
replacement archives. The original throttleit 1.0.1 and de-indent 1.0.2 author
notice gaps remain recorded as unresolved historical facts. Their measured
replacement/removal affects current selection only. The current report has two
selection remediations and seven remaining selected author-notice gaps; neither
this patch nor that report asserts full redistribution or release qualification.

Retire the override when a selected upstream request-progress dependency already
uses an equivalent notice-bearing compatible throttle release. Retire the compiler
removal when a selected upstream Mainsail manifest removes the unused declaration,
or reassess it if upstream introduces a real caller. No upstream message was sent.
