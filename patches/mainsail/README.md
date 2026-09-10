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
