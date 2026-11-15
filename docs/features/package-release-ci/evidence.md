# Package and release-gate CI delivery

## Delivered behavior

The new `Package and release regressions` workflow runs on relevant pull requests, main pushes and manual dispatch. Shared path filters cover scripts, tests, configs, patches, runtime, UI, extensions, upstream gitlinks/lock, project licensing, workflow and documentation changes. It runs thirteen explicit offline suites without building full images, mounting live images, compiling ARM64 packages or activating services. Keep the runner's `SUITES` list current when adding a new relevant suite.

The runner fails on test failure, discovery/import error, missing/empty/duplicate selection, unknown source metadata or any skip. It continues ordinary failing suites to retain later results. Each UTF8 suite log is bounded to128KiB and retains late diagnostics with a truncation marker. Preparation pipelines preserve bounded error tails and propagate nonzero status. An `always()` action uploads source revision, summary, suite logs and preparation logs with seven-day retention and an error on absent files.

Actions are pinned, contents permission is read-only and checkout credentials are not persisted. Only the exact public Mainsail submodule is prepared. A150046-byte supplier fixture is fetched with1MiB/60second bounds and selected SHA256/SRI verified, enabling both real gcodeviewer/standard-license tests with zero skips; no supplier installer runs.

## Actual acceptance evidence

| Check | Actual result |
| --- | --- |
| Local selected runner | 127tests across13suites passed, zero skips |
| Hosted code candidate `0fbad4f73ea5ade7989e5bfd45a350908c21e4aa` | [Run39907153416](https://github.com/drew442/sv08-mainline/actions/runs/39907153416) succeeded;127tests/13suites/zero skips, clean source |
| Failed-test upload control `ace257a89dda21744544f7d5e0163bfb915dd955` | [Run39907398337](https://github.com/drew442/sv08-mainline/actions/runs/39907398337) ran all127real checks successfully, then an explicitly deliberate1test fixture failed; upload step still succeeded |
| Final workflow restoration | Exact original validated workflow SHA256 restored; temporary failed-test step absent |
| Runner failure/outcome regressions | Six tests prove later-suite execution, failure logs/source summary, missing/zero/import/skip refusal, bounded Unicode logs and late failure diagnostics, both actual preparation-shell wrappers' nonzero failure/log retention and input-trigger matches |
| Static checks | Complete stable diff, JSON summary, YAML alias/embedded verifier syntax and doc links inspected; diff check passes |

Suite coverage and actual counts:

| Suite | Tests passed |
| --- | ---: |
| `test_package_klipper.py` | 6 |
| `test_package_policy.py` | 3 |
| `test_package_rauc.py` | 5 |
| `test_package_update_admission_license.py` | 3 |
| `test_python_app_package.py` | 3 |
| `test_klipper_build_inputs.py` | 9 |
| `test_prepare_release.py` | 13 |
| `test_image_license_inventory.py` | 14 |
| `test_license_inventory.py` | 20 |
| `test_project_license.py` | 18 |
| `test_resolve_npm_notices.py` | 21 |
| `test_mainsail_notice_dependencies.py` | 6 |
| `test_package_release_ci.py` | 6 |

Package/native input tests include source hash, identity, patch/lock/wheel mismatch and operation refusals. Release/source/notice tests include altered/missing/stale provenance, slot payload/package disagreement, malformed/truncated images and mount cleanup, supplier/archive tampering, exact standard-text export and stale/missing/corrupt inputs. These are deterministic regression fixtures; they do not replace mandatory actual-image release qualification.

The first actual hosted artifact contains all13suite logs, two bounded preparation logs, summaryJSON/text and source-revision.txt. The failed-test artifact contains all14suite logs (including the deliberate failure), both preparation logs and a failing summary. Actual job-step metadata confirms only the deliberate probe failed and the upload succeeded. The probe intentionally creates an untracked failing fixture, so its metadata truthfully records dirty=true; it is not source/release qualification. No probe step remains in the final workflow. Final-head CI results are recorded separately in the existing project goal/task records and PR; earlier receipts retain their actual source revisions.

| Retained evidence | Identity/hash |
| --- | --- |
| Initial failed local Mainsail log | `746eed064977e50cc879a0dd108d2472123505976d4882369660c43a36c48382` |
| Passing local runner summary | `721109c56cb3e8c8cd7224f4ca7f300d7a764ab2f4945be58273bcf13bfc0b28` |
| First hosted passing summary | `49c1786eea639db0700761cc0dbac2f4e6e1bc928d1713bedd7c0ab75a90cb07` |
| Actual failed-test hosted summary | `e594a9cd45e3507d4df5f8bef2cb1befbefd9b07644e91c2371c1f5f00c15dbd` |
| Passing artifact | ID12481580862,8896bytes; service archive digest `a6fa96fa8dba1515f463e461763393652601b250ba504d8e7b94d7e28263540a` |
| Failed-test artifact | ID12481367269,8938bytes; service archive digest `d444d7fc8e6c0ce98e82b155d2a87e935b96353f92581712346caf5244ae7587` |
| Final workflow | `44871a75a6911db2e864872abc1baef48a95e75f60055a8a00139c994f1d26f6` |

Artifact metadata/digests are reported by GitHub; downloaded extracted summaries/logs were actually inspected and individually hashed. Raw sanitized logs and summaries remain in `/home/drew/.sv08-package-ci-20261023`. The first hosted checkout's actual merge revision is `22f6b1f0a35279f698e22eb4e816784c6d637173`, distinct from the PR head; source-revision.txt and runner summary agree.

## Diagnosed correction and preserved attempts

Initial local selection ran125tests with124pass/1failure/zero skips: the newly selected existing historical Mainsail test's expected full coverage dict omitted `accepted_distributor_standard_terms:0`. The fixture represents an earlier lock without standard-term acceptance. The correction adds that exact zero while retaining every historical count and equality assertion; production accounting, inventory, source guards and release gates are unchanged. Failed logs and initial source candidate/branch remain preserved. Exact file ownership was extended through existing authorization/claim records before editing the assertion; no owner requirement or historical evidence hash was silently replaced.

Local invocation:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$SCRATCH" SV08_GCODEVIEWER_ARCHIVE="$SCRATCH/gcodeviewer-3.7.18.tgz" python3 scripts/check_package_release.py --output "$SCRATCH/selected-run-2"
```

The exact supplier fixture and Mainsail gitlink must be prepared first, as the tracked workflow does. No missing prerequisite is silently skipped. A six-test runner suite additionally exercised both actual preparation pipeline wrappers with deliberate failing commands and large output. The hosted negative probe was a separate, bounded acceptance control; the final source restores the exact tested normal workflow, not a weakened check.

## Authority, resources and limits

One fresh named project_implementer child (`/root/package_ci_impl`) used the repository default requested Sol/low route, resumed for the related bounded correction without changing effort. Effective runtime settings/thread ID were not exposed; no independent-review or savings claim. Coordinator handled records, publication, actual hosted execution/artifact inspection and temporary failure-probe/restoration.

Primary allowance1800cumulative process-seconds/512MiB local generated plus normal hosted execution per changed candidate. Worker conservatively charged under20process-seconds/~20MiB including both source clones; coordinator workflow/read/Git/artifact overhead is conservatively charged600seconds/32MiB, cumulative budget retained across scope renewal and probes. No OS images/compiler roots/new infrastructure or host dependency installs. Hosted fixture/source downloads use existing standard CI tools.

Actual pull-request execution and success/failure upload behavior were exercised. Main-push/manual triggers and input paths are source-tested and declared; those events await owner merge, and no main/manual hosted execution is claimed. Artifact retention is seven days, not permanent archival; abrupt runner loss can still prevent upload. No merge, deployment, printer access, hardware, complete-image, full rebuild reproducibility or actual release qualification is claimed.
