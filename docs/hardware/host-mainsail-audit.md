# Mainsail dependency review

Reviewed 2026-09-10 at source pin `32f99e1cf97640b23a52829dfa3a0aceee11d382`.
This is an initial source/release review, not a clean security bill or a completed
browser workload test. The original npm audit reported 17 findings (8 low,
6 moderate, 3 high); the patched lock reports 15 (8 low, 6 moderate, 1 high).

## Fixed compatible dependencies

[The recorded patch](../../patches/mainsail/0002-pin-fixed-yaml-nanoid.patch)
selects js-yaml 4.3.2 and nanoid 3.3.18 with registry integrity hashes. The builder
verifies the original lock, patch and resulting lock before `npm ci`. It does not
modify the upstream checkout or update unrelated dependencies.

The js-yaml maintainer documents CPU exhaustion through repeated empty merge
sources and the 4.3.2 fix. The lock marks this dependency as development-only;
no direct application import was found. Fixing it still protects source tooling.
[Maintainer advisory](https://github.com/nodeca/js-yaml/security/advisories/GHSA-2883-xcg3-v3hh).

Nano ID's 3.3.18 release completes the zero-size custom-generator fixes. The
observed PostCSS caller uses `nanoid/non-secure` with a fixed size of six, and no
direct application import was found; that is narrower than proving absence from
every generated asset. [Maintainer release](https://github.com/ai/nanoid/releases/tag/3.3.18).
The [bounded regression](../../tests/mainsail_fixed_dependencies.cjs) checks both
zero-size custom generators and the empty-merge limit, plus an ordinary YAML load.

## Remaining findings and reachability

| Finding group | Evidence at this pin | Required follow-up |
| --- | --- | --- |
| Vuetify prototype pollution | `src/plugins/vuetify.ts` constructs Vuetify from literal options; no imported user preset reaches that constructor in the inspected code. | Test configuration/theme import boundaries; plan a maintained framework migration or reviewed fix. |
| Vuetify date-picker XSS | No `v-date-picker`, `VDatePicker` or `title-date-format` use was found in application source. This does not prove tree-shaking removed all component code. | Verify generated/browser paths and regress if date-picker use is introduced. |
| ECharts Lines-series tooltip XSS | `src/main.ts` registers LineChart, BarChart and PieChart, not LinesChart; heightmap separately registers SurfaceChart. LineChart and LinesChart are different components. | Test charts, especially custom HTML tooltip formatters; choose a compatible upstream upgrade/fix before claiming resolution. |
| Vue runtime/compiler and dependent wrappers | Vue 2.7.16 remains selected; template compiler is a development dependency, but version-only audit output cannot establish whether runtime template compilation is reachable. | Trace compiled assets and imported configuration/HTML, then test browser input boundaries and migration options. |
| Joi, qs, Vitest/mocker | Lock records these as development dependencies. Production ships static assets rather than a Node development/test server. | Update compatible toolchain dependencies, rerun unit/build tests and verify the production artifact boundary. |

The Vuetify findings involve constructor preset merging and date-title HTML,
respectively; the reporter also documents the lack of public Vue 2-era fixes.
[Prototype-pollution report](https://www.herodevs.com/vulnerability-directory/cve-2025-8083),
[date-picker report](https://www.herodevs.com/vulnerability-directory/cve-2025-8082).
The ECharts upstream fix changes `src/chart/lines/LinesSeries.ts` and includes a
browser regression. [Upstream fix](https://github.com/apache/echarts/commit/1e39b00eedda0e4a0b048e099c0e13ce7149d90f).
All linked sources were accessed on 2026-09-10. The table's application
reachability statements are source-based inferences, not exploitation results.

## Build evidence

Fresh archive/npm/Vite builds in `build/mainsail-package-v7/` and `v8/` produced
identical `sv08-mainsail_2.19.0+git32f99e1c-4_all.deb` packages:
`6861b281cfdc19d1073c46aaf442e97ba7ba55e40fd97ff6d2552fd7b4310df1`.
Both include the existing stable precache patch. Build logs remain beside the
work directories. Both builds' disposable node_modules directories were removed to free
workstation space after their regressions; source archive, patched lock, output and
report remain. The package has no service activation and has not been installed
on the printer or substituted into older capacity/boot evidence.

The [browser startup probe](../../tests/mainsail_browser_startup.mjs) served the
patched dist on a temporary loopback port and controlled the existing Chrome for
Testing 145.0.7632.6 via its debugging protocol. It mounted the Vue application
with zero uncaught JavaScript exceptions and rendered the expected connection
waiting dialog. No Moonraker service or printer was connected. The screenshot,
DOM, exception list and result are in `build/mainsail-browser-v3/`; test browser
and server processes were stopped afterward. Earlier `--dump-dom`/virtual-time
attempts timed out without output; they are not application failure evidence.
The direct protocol probe passed. This is static startup evidence, not dashboard,
chart, upload, authorization or print-workflow validation.

The [public evidence](host-mainsail-audit-20260910.json) records the build and audit
counts separately from the limited browser result. The next steps are a local
API fixture and browser workload coverage, remaining compatible tooling fixes,
and reviewed treatment of the framework findings. Version-based findings remain
visible until their fix or narrowly supported reachability disposition is tested.

## Packaged API and file roundtrip

The subsequent `build/mainsail-api-browser-v4/` run used the real packaged ARM64
Moonraker 985c1d0 under QEMU user emulation and Chrome in one temporary network
namespace containing only loopback. The fixture used a new disposable data tree,
`provider: none`, trusted loopback and an absent Klipper socket. The browser
completed its initialization list, reported the expected API version and
Klipper-disconnected state, then uploaded, read back and deleted a harmless
configuration file. There were no uncaught JavaScript exceptions. No physical
network interface, MCU or printer service was available in that namespace.

[The fixture runner](../../tests/host_moonraker_browser.py) records the method and
requires explicit execution, build-directory paths and a non-deployable manifest.
Run it through `sudo unshare --mount --net --pid --fork --mount-proc` with explicit
`--rootfs`, `--output`, `--node`, `--chrome` and `--dist` arguments. Its network
check uses namespace-local link information; the host's pre-existing sysfs mount
can still describe host interfaces and must not be used for this check. The first
15-second API deadline was too short for source compilation under user emulation;
the successful run allowed 900 readiness polls with 100 ms retry delays
and a one-second HTTP timeout. This is not an ARM hardware startup timing.

The documented runner repeated this result in `build/mainsail-api-browser-v5/`.
The test data was deleted and namespace/browser/API processes stopped afterward.
Logs, server-info response, screenshot, DOM and browser result remain in the
fixture output. Optional theme files were absent as expected. Internet announcement
fetches failed in the intentionally disconnected namespace. This validates a
trusted-loopback API/file path, not production authentication or a print workload.
