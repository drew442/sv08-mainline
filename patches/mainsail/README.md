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
