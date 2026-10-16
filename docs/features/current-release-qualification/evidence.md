# Complete current-image software qualification

The complete **7,818,182,656-byte A/B plus independent-recovery image** passed the actual default `selected-software` release gate. Actual altered-payload and missing-artifact cases were refused without publishing evidence packages; the original image and input were restored exactly. Review publication is pending.

This is **software/source preparation evidence for a non-deployable diagnostic image**. Hardware, printing, recovery execution, legal compliance and complete-image reproducibility are not qualified. No printer operation, flashing, deployment or merge occurred.

## Artifact and source identities

- Image SHA256: `2695e3585d3d6cf4a17dbf56a3543dd54bd316373401b71c8e7c58686502984a`.
- Image build source: `e03db7308e152b8ecf61f18e493a1b5038a10832`.
- Qualification-tool source: `a81b48503cabad4b70dad8af272de18d857ef69e`.
- Anonymous [corresponding-source archive](https://codeload.github.com/drew442/sv08-mainline/tar.gz/e03db7308e152b8ecf61f18e493a1b5038a10832), SHA256 `1ac2c30a59b3cc15f99b2fa87e9a61b20b4d022dc2bc83e2676a640958a952a2`.
- Release evidence manifest SHA256: `5dfa80cef94bd4f5695bc4bbcaa4b24075f290ec305893fe53c337ca0defce1c`.
- Exact partition, source, tool, receipt and exported-file hashes are in [evidence.json](evidence.json).

The later inspector fix changes nested-loop cleanup and its tests. Runtime, configuration, application pins, catalog, extension, patches and lock bytes remain unchanged from the image source. The existing image/release/public-source identity remains at e03db730; no historical provenance was refreshed to label it as a81b485.

## What the actual gate established

The official composer produced all six partitions and preserved its host, recovery and data sources. Actual image partition hashes equal all six component hashes. Offline readback also matches the exact reviewed SPL and both environment copies. Normal-root fresh finalization ran real `dpkg --audit` and `apt-get check`, verified the pinned board inventory and required persistent identity hooks, and retained diagnostic service masks.

The gate inspected both normal roots (514 installed packages and 26,951 software inventory entries each) and recovery (286 packages and 21,113 entries). Every software root passed anonymous exact corresponding-source qualification. All six selected applications match their package identities and complete supported software payloads in both normal roots, including 5,138 opt payload entries per normal root.

| Selected package | Version | Matching partitions | opt entries |
| --- | --- | --- | ---: |
| sv08-klipper | `0.0+gitf0892d82-2` | 2, 4 | 1572 |
| sv08-klipperscreen | `0.0+git3791fdf7-2` | 2, 4 | 1590 |
| sv08-mainsail | `2.19.0+git32f99e1c-10` | 2, 4 | 0 |
| sv08-moonraker | `0.11.0+git985c1d0b-2` | 2, 4 | 1975 |
| sv08-update-admission | `0.1.0-3` | 2, 4 | 1 |
| rauc | `1.15.2-0sv08.2` | 2, 4 | 0 |

Recovery has its independent software/package provenance; selected normal applications are required in A and B. The exported notice inventory inspected 897 supplier archives: 896 dependencies have notice text, one uses the separately recorded standard LGPL terms, and zero have unresolved declaration-only coverage. The historical missing embedded notice remains recorded; no author attribution was invented.

All ten exported files are present; nine content hashes verify against `release-manifest.json`. These include actual-image/software inventories, package bindings, anonymous source pins, supplier notices, standard LGPL text and the scope report.

## Actual refusal checks

1. Appended a synthetic comment to the actual regular Klipper executable in normal A. B's partition hash remained unchanged. The default gate exited 1 for the expected application identity/payload mismatch in a required normal slot; no package was published.
2. Restored A from its immutable component with a bounded extent write and fsync. The entire image SHA256 again equals the original artifact hash.
3. Temporarily renamed one exact selected application archive in the assigned transported inputs. The default gate exited 1 for that missing pinned artifact; no package was published. Restored the original path and pinned hash, with the image still exact.

No second full image was created. Exact failure logs and restoration evidence remain in the assigned artifact directory; the JSON records their hashes and actual outcomes. The first missing-input gate correctly refused the archive, but its harness over-specified an absolute error path. The corrected check requires the exact relative pinned path; only that case was rerun, with the original failure retained.

## Reproduction entry points

Construction used `prepare_host_os.py` with `configs/images/host-ab.json` (bootstrap, packages, refresh), the pinned application/board/Cockpit archives, `integrate_host_os.py`, canonical `stage_printer_ui.payload()` plus `stage_admin_ui.stage(..., refresh=True)`, and `finalize_diagnostic_host.py --fresh`. Recovery assembly/derivation received the exact release manifest and board profile; `build` verified their inherited binding without refreshing it. The official `assemble_board_diagnostic.py` created the disk.

The actual positive command, from the assigned Beelink checkout, was:

```sh
sudo python3 scripts/prepare_release.py \
  --image build/current-release-disk/sv08-board-diagnostic.img \
  --public-source /home/drew/.sv08-current-release-20261015/public-source.json \
  --inventory-inputs /home/drew/.sv08-current-release-20261015/remote-inventory-inputs.json \
  --scratch /home/drew/.sv08-current-release-20261015 \
  --output /home/drew/.sv08-current-release-20261015/release-evidence
```

No narrower profile was selected. The assigned handoff retains exact construction commands, package pins, scratch recipes and process results. The evidence package and image must remain together and match their hashes.

## Repairs required by the real image

- Include supported `opt/sv08-mainline` payloads and require selected applications in **both** normal roots, preserving recovery's separate scope and generic single-root compatibility.
- Bind exact diagnostic release bytes and final project provenance to recovery assembly/derivation/build, without changing old receipts or bypassing source-preservation checks.
- Support truthful first-time normal-root finalization from actual completed profile/package stages, without inventing a prior copied-root receipt.
- Recognize only exact generated Mainsail/nginx seed outputs, with the public-key seed separately hashed as a non-code build input. Unknown/changed code stays unqualified; key drift invalidates provenance.
- Preserve the pinned admission package extension through fresh/refresh core integration. Unexpected files and symlinks in that subtree fail before mutation.
- Restore the recovery handler's executable mode before strict staging.
- Unmount and detach nested image loops from inner to outer; failed unmounts retain the associated loops. The original real cleanup failure and manual owned-loop cleanup are preserved.

Fresh UI composition used canonical printer payloads before host staging. Supported refresh reconciled the matching core catalog; exact stock Debian logo aliases were removed before project branding. These were disposable invocation corrections, with existing source/symlink guards retained.

## Validation and limits

Relevant passing checks: 13 release-preparation, 14 inventory/cleanup, 28 recovery, 18 project-provenance, 9 fresh-finalizer, 4 composer, 11 board-contract, 7 admission-integration and 35 boot-health tests, plus six focused provenance checks and 24 relative documentation links. Focused checks overlap larger suites; these are not presented as a combined unique-test count. Unchanged implementation/test hashes support evidence reuse; the actual complete-image runs provide the integration evidence.

Commissioning tests have three dependency-source guard errors and one deliberately opt-in selected-tool skip, reproduced on unchanged main (14 passed, 3 errors, 1 skipped). They were preserved, not weakened or presented as a pass. Initial rootless fixture, scratch-permission, import-path and recovery timeout failures also remain preserved.

Named task-scoped agents handled source tracing, source/provenance and finalization work, admission preservation and loop cleanup. Semantic admission/source repairs requested medium effort; settled work and lookups used normal default-low roles. Effective settings were not independently observable. The coordinator performed self-validation; no independent review or measured savings are claimed.

The full image and ten-file evidence package remain on Beelink under `/home/drew/.sv08-current-release-20261015/`; the local handoff is at the same assigned path. Disk images, credentials, private keys and raw configuration/data dumps are not published in this PR. Only a new disposable public access key was seeded.

Deferred qualifications are the gate's explicit hardware/recovery-execution/legal/full-reproducibility limits and the separately retained commissioning guard failures. Printer services, activation and boot health stay masked in this diagnostic artifact.

After successful refusal/restoration checks, verified superseded 83 recovery roots/payloads and the six unused composition components were removed. Source branches, historical receipts/logs, current construction inputs, the single qualified full image and its evidence remain. Observed free space after cleanup: about 6.1 GiB locally and 14.7 GiB on Beelink. Cumulative generated-data accounting was not reset.
