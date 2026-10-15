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

## Native ESM Vitest diagnostics without stackback

`0004-vitest-notice-closure.patch` follows patches 1–3 at the same upstream
revision. The root test-runner edge selects exact upstream `vitest: "5.0.4"`.
Its native ESM hanging-process reporter imports exact `why-is-node-running: 3.2.1`,
whose supplier archive includes Mathias Buus's full MIT notice and has no runtime
dependencies. This removes the former `why-is-node-running` 2.3.0 diagnostic path
through `siginfo` and `stackback`; it preserves the actual diagnostic functionality.
The original stackback notice gap remains a historical fact, not a relicensing.

The aligned selected family is Vitest, `@vitest/mocker` and `@vitest/spy` 5.0.4.
Vitest 5 bundles the former expect, runner, snapshot, utils and pretty-format
packages; their separate records and unused pathe/tinyrainbow children disappear.
Required companion updates are chai 6.3.0, es-module-lexer 2.3.2, obug 3.0.0,
std-env 4.3.0, tinybench 6.2.2, tinyexec 1.3.1, the two runner/mocker-local
magic-string copies 1.4.3 and runner-local picomatch 4.0.7. Magic-string requires
sourcemap-codec 1.6.0. The root Node type range changes to `^22.0.0`, selecting
22.20.5, to satisfy Vitest's peer range while matching the actual pinned Node 22
runtime. Pinned Node 22.23.2 and selected Vite 8.1.2 satisfy Vitest's declared
engine and peer ranges. Supplier metadata is retained exactly, not rewritten to
make incompatible dependencies appear compatible.

The lock-generation procedure remains the disposable archive procedure above,
now after patches 1–3 and these two manifest edge edits. Retain original unrelated
`libc` fields rather than npm's removals, as before. The resulting patch changes 15 supplier records
and the root record, removes 10 records and adds no record paths. All other
records, including production dependencies and earlier fixes, remain identical.
The profile pins patch 4, the complete resulting lock and artifact revision 6.

The [offline tests](../../tests/test_mainsail_notice_dependencies.py) enforce that
complete delta and the exact Vitest/diagnostic SRI values. The existing historical
accounting fixture deliberately retains its patch-3 selection so its earlier
removal/replacement protections remain exercised. Current full-69 accounting is
regenerated separately against the final lock and exact supplier archives.

Run the [runtime regressions](../../tests/mainsail_notice_dependencies.cjs) with
the pinned Node and a fresh installation's `node_modules` under a 40-second
external timeout. In addition to the earlier dependency protections, this runs
the real Vitest CLI twice against a disposable passing test: clean exit, then a
main-process timer created after reporter initialization. The latter must report
the supplier's tracked Timeout and fixture location through the built-in
`hanging-process` reporter, reach Vitest's own 200ms teardown timeout, and exit
successfully. Each child has a 15-second process bound and is reaped; the fixture
is removed. The actual unchanged upstream unit suite and coordinator-owned clean
package builds/startup checks provide compatibility and repeatability evidence;
source tests alone do not establish these outcomes or release qualification.

Primary upstream sources: the exact [Vitest 5.0.4 supplier archive](https://registry.npmjs.org/vitest/-/vitest-5.0.4.tgz)
and [why-is-node-running 3.2.1 supplier archive](https://registry.npmjs.org/why-is-node-running/-/why-is-node-running-3.2.1.tgz).
Their package metadata, native reporter implementation and embedded notice were
inspected at this continuation. No supplier bytes, upstream gitlink or license
wording change. Retire this patch when the selected upstream Mainsail runner
already provides the compatible native ESM diagnostic dependency path. No upstream
message has been sent.

## Licensed Janus SDK and independent streaming adapter

`0005-janus-sdk-replacement.patch` replaces the sole `typed_janus_js` consumer
with the complete, exact 117451-byte Meetecho MIT SDK and an independently authored
narrow adapter and declarations. The SDK is extracted from `sourcesContent[0]`
(`../js/janus.js`) in the existing supplier's `package/dist/index.esm.js.map`.
[Provenance](../../configs/host/mainsail-janus-sdk.json) pins the original archive
SHA256/SRI, source-map member, complete source, notice and added ESM export tail.
No wrapper implementation or declarations were copied, and no grant for the wrapper
is inferred. The SDK bytes are unchanged; `\nexport default Janus;\n` is the only
added SDK tail. Upstream LICENSE and source revision remain unchanged.

The full SDK notice is copied unchanged to `public/licenses/janus-sdk.txt`, so
bundler comment removal cannot discard it. Independently authored adapter/types
and source tests carry AGPL-3.0-or-later headers; the full project grant is shipped
as `public/licenses/sv08-janus-adapter-AGPL-3.0.txt`. The coordinator maintains the
application-source notice inventory separately from historical NPM accounting.

The adapter uses the existing selected `webrtc-adapter` 9.0.3 supplier directly.
A genuine lock-only npm invocation after patches 1–4 removes the wrapper, aigle,
aigle-core, wrapper-local TypeScript/TypeDoc and their now-unused documentation
children: 23 records disappear, no paths are added, and only the root record
changes. All surviving supplier records are retained byte-for-byte semantically,
including unrelated libc and dev metadata rewrites npm attempted. The previous
wrapper-only lodash override is removed. The exact complete delta is tested; the
profile pins patch 5, the resulting lock and package revision 7. Pinned Node/npm,
install-script restrictions and all previous patches remain in effect.

The production component retains its URL derivation, numeric stream ID, ICE
configuration defaults, createAnswer defaults, video attributes and presentation.
The independently authored lifecycle invalidates stale callbacks immediately,
clears tracks/video and waits for SDK destroy success/error (or a thrown destroy)
before starting its successor. Pending session creation is also cleaned up before
a successor starts; rapid changes retain only the latest waiting run. Session,
plugin/watch/start/answer, ICE and synchronous errors become visible error status.
A stopped or superseded run cannot attach media or update successor state.

[Offline regression tests](../../tests/test_mainsail_janus.py) apply pinned patches,
check exact source/notice/public grant, unchanged upstream LICENSE and component
presentation/addressing, and the complete lock delta. Set `MAINSAIL_JANUS_ARCHIVE`
to the retained supplier archive to additionally verify archive SHA256/SRI, member
hash and actual source-map extraction. Earlier patch-3 and patch-4 delta fixtures
remain in [dependency tests](../../tests/test_mainsail_notice_dependencies.py).
The patched upstream `tests/janusStream.spec.ts` exercises successful negotiation,
status/tracks, stopped pending initialization/session, stale callbacks, failures,
delayed destroy success/error/throw and rapid restart/stop ordering.

The [browser harness](../../tests/mainsail_janus_browser.mjs) takes `--execute
CHROME SOURCE OUTPUT JANUS_URL STREAM_ID RTP_PORT` in an isolated namespace with
only `lo` and dummy `sv08test0` at `192.0.2.1/32`, with no default route.
The dummy documentation address permits libnice ICE candidate gathering, which
excludes loopback addresses; signaling and RTP input remain on loopback.
It serves the production adapter through Vite, encodes deterministic VP8 canvas
keyframes using Chromium WebCodecs, sends actual RTP into a disposable Janus
streaming fixture, and checks decoded video dimensions/frame progress, restart
and destroy. Its explicit empty ICE list is fixture-only; production defaults are
unchanged. External HTTP requests are blocked and processes/timers/sockets are
cleaned up. This exercises actual SDK/WebRTC playback, while the production Vue
component's presentation is checked separately; it does not qualify a camera or
printer. Coordinator-owned full unit/type/build/startup and repeatability results
remain separate evidence. Retire the patch when selected upstream Mainsail has a
notice-bearing, tested equivalent dependency path; no upstream message was sent.

## Independent native visibility directive

`0006-native-visibility.patch` replaces the selected `vue-observe-visibility`
1.0.0 dependency with an independently authored directive using the browser's
IntersectionObserver and Vue 2 lifecycle. It implements only the function-valued
bindings actually used in the nine pinned consumers. Their source bytes remain
unchanged, including editor focus, preview creation, webcam request gating and
chart callbacks. Unused library options, thresholds, throttling and once behavior
are not an application contract and are not reimplemented.

The shared [Vue 2/Chromium harness](../../tests/mainsail_visibility_browser.mjs)
was run against the original installed plugin before the directive was authored.
The measured contract includes an initial visible or hidden result after consumer
initialization, boolean transition deduplication, native viewport/nested clipping,
visible exact-edge contact and in-viewport zero-area targets. Unrelated Vue updates
do not reset observation. Replacing the callback gives its successor a fresh
initial result. Removal before queued initial delivery produces no callback.
The replacement defers observation with Vue.nextTick, retains per-element state,
disconnects on replacement/unbind and invalidates already queued stale delivery.

The harness accepts `--execute CHROME SOURCE OUTPUT baseline|candidate` and must
run in an isolated network namespace with only loopback up. A minimal Vite server
loads the real pinned Vue runtime and selected directive without bootstrapping the
application. An explicit script-free HTML middleware route runs before SPA
fallback. Dependency discovery is disabled (`entries: []`, `noDiscovery: true`),
with only Vue and the original plugin (baseline mode) explicitly prebundled in
a fresh output-local cache. The harness rejects application-entry requests and
unexpected navigation/reloads and records all requests and navigations. External
HTTP requests are blocked. It records the complete trace of
33 stages, including actual scrolling, hidden/revealed and component-root targets,
independent targets, repeated mounts and representative focus/preview/request/chart
effects. Candidate mode requires `VISIBILITY_BASELINE=/absolute/result.json` from
the original run and compares that trace without changing its expectations. Vue's
actual version is recorded and checked. These are representative fixture consumers;
the nine production components are protected separately by exact source comparison.

[Offline checks](../../tests/test_mainsail_visibility.py) apply all six pinned
patches with zero fuzz, preserve the upstream LICENSE and existing public project
AGPL grant, check all nine consumers and enforce the complete manifest/lock delta.
The source patch includes eight focused lifecycle tests, including browserless
import, missing API, stale delivery, deferred cleanup and callback replacement.
Run `node node_modules/vitest/vitest.mjs run tests/observeVisibility.spec.ts` with
the pinned Node executable in the prepared source installation. Independent source
and test files retain AGPL-3.0-or-later headers under the existing public project
grant. No library implementation is copied, and no missing supplier grant is inferred.

An environment without IntersectionObserver requires a compatible polyfill loaded
before Vue mounts. Browserless import is safe and unsupported observation emits no
visibility result; it never assumes visible. Actual Safari 12 behavior has not been
exercised and remains an explicit limitation of the existing target. Chromium fixture
results do not establish Safari, printer or camera qualification.

The genuine npm lock-only procedure removes just the root dependency and the
`node_modules/vue-observe-visibility` record, preserving every surviving supplier
record. As with earlier patches, unrelated npm rewrites of libc and
dev/peer/optional metadata were excluded; original surviving supplier records
were retained. The profile pins patch 6, the final lock and artifact revision 8. Earlier
patches, upstream source/gitlink, Node/npm pins, disabled install scripts and all
earlier protections remain unchanged. Coordinator-owned full unit/type/build/startup,
two fresh reproducible packages and current notice accounting provide separate
integration evidence. The original dependency's missing author notice remains a
historical fact; measured removal does not relicense its source. Retire this patch
when selected upstream Mainsail supplies an equivalent tested, notice-bearing
visibility mechanism. No upstream message has been sent.

## Independent Cypress operating-system paths package

`0007-ospath-compat.patch` supplies the independently authored
`@sv08-mainline/ospath-compat` 1.0.0 package under the project's full existing
AGPL-3.0-or-later notice. Its CommonJS exports are `home`, `data`, `desktop`,
`tmp` and mutable `__platform`. Authoring used recorded black-box results for
32 platform/environment scenarios and 32 mutation stages, without reading or
copying the original ospath implementation. Native `os.homedir` takes precedence;
legacy environments use HOME or USERPROFILE. Environment and platform values are
read on each call, while path normalization uses the host Node path module.
Missing required environment values retain the observed TypeError behavior.

The root manifest declares development dependency `ospath` as
`file:vendor/sv08-mainline-ospath-compat-1.0.0.tgz` and uses the Cypress-scoped
override `cypress: { ospath: "$ospath" }`. npm's dependency key remains
`ospath`; the actual archive and lock identity is the distinctly named authored
package. The direct root edge establishes the local package before Cypress's
scoped edge is resolved, avoiding the defective nested relative fetch path.
Cypress, its existing test and interactive-open scripts, and application consumers stay selected. This is a
distinct project component, not an ospath supplier release or a new grant for the
historical archive. No upstream license, gitlink or supplier bytes change.

The builder constructs the tarball before `npm ci` from four explicitly pinned
files in patched `vendor/ospath-compat`. The profile pins their complete hashes,
actual authored identity and deterministic archive hash. Archive members are
validated ordinary files with fixed order, modes, owners and zero timestamps;
gzip omits filename and wall-clock metadata. Symlinks, extra files, unsafe names,
wrong identity, changed sources and incomplete project notice fail closed.
There is no encoded binary patch, registry publication or install lifecycle.

Regenerate the lock only in a disposable source after all patches. First call
`package_mainsail.prepare_authored_archives(source, config)` with the selected
profile; then use pinned Node/npm and isolated existing cache/config with
`npm install --package-lock-only --ignore-scripts --no-audit --no-fund`.
Preserve the original and generated lock evidence and pin the genuine resulting
lock and source patch before building. The initial real-lock generation exposed
npm's inconsistent root-versus-parent relative override resolution; its retained
failure and the failed bounded stale-record repair are retained separately from
the earlier synthetic feasibility result. The approved graph correction adds the
explicit root development edge and scoped reference described above; it is a
changed graph,
not a retry of the failed stale-record approach. Two genuine offline lock-only
npm invocations with separate empty caches produced byte-identical raw output.
As in earlier patches, unrelated libc/dev/peer/optional metadata rewrites were
retained at their original values; the final lock changes only the root record
and `node_modules/ospath`. It records the actual authored package name, local
archive and SRI, with no original ospath archive selected. The profile pins the
complete resulting lock and patch. Relocated fresh `npm ci`, replacement Cypress
acceptance and two fresh reproducible packages remain coordinator-owned checks.

[Source checks](../../tests/test_mainsail_ospath.py) verify the complete measured
contract, manifest scope, original test scripts, deterministic source/notice
binding and exact selected lock delta. The
[portable contract fixture](../../tests/mainsail_ospath_compat.cjs) contains
observations only. The patch also supplies focused upstream Vitest checks.
Coordinator-owned actual Cypress CJS/ESM/CLI, E2E and interactive-open checks
remain necessary; the API fixture alone cannot establish runner compatibility.

Selection accounting accepts an authored replacement only through explicit
profile pins. Its replacement archive input includes `authored_source`, a
standard file pin for the patched root `package.json`. The resolver validates
that manifest's local root development edge and scoped reference, all authored
source hashes, complete project notice, exact archive bytes, selected identity,
local path and SRI. It reports
`replaced-by-source-bound-authored-package` separately from supplier releases.
Original69 historical records and the original60 supplemental records retain
their existing facts; replacement does not resolve the original missing grant.

Retire this package when the selected Cypress dependency provides an appropriate
notice-bearing compatible path implementation. No upstream message was sent.
