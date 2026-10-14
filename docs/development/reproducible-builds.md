# Reproducing the selected software packages

The [build closure evidence](../features/build-license-closure/evidence.md) distinguishes independent source builds, fresh package assemblies and repackaging supplier binaries. It covers the selected project packages, not a bit-identical complete boot image or a printing release. Do not replace historical results with new hashes.

Klipper `0.0+gitf0892d82-2` selects the reproducibly built helper and MarkupSafe wheel in [klipper-build-inputs.json](../../configs/host/klipper-build-inputs.json). The upstream host/MCU commit, source code, optimization flags and physical configuration are unchanged. Canonical compiler paths and a recorded source epoch remove workspace-dependent debug/timestamp output. Historical hashes remain in the recipe. Admission `0.1.0-3` includes hash-pinned project license/grant notices and carries the corresponding exact Klipper dependency; its extension source is unchanged.

Use existing tools with the exact recorded versions. Supply a fresh coordinator-owned scratch directory and an explicitly assigned disposable ARM64 compiler root; the builder neither installs tools nor prepares that root. No printer operation is required. For example, with `SV08_TASK_SCRATCH` and `SV08_COMPILER_ROOT` assigned by the coordinator:

```sh
python3 scripts/build_klipper_inputs.py --kind helper \
  --source upstream/klipper --work "$SV08_TASK_SCRATCH/helper-a" --execute
python3 scripts/build_klipper_inputs.py --kind helper \
  --source upstream/klipper --work "$SV08_TASK_SCRATCH/helper-b" --execute
python3 scripts/build_klipper_inputs.py --kind markupsafe \
  --source "$SV08_TASK_SCRATCH/sources/MarkupSafe-1.1.1.tar.gz" \
  --compiler-root "$SV08_COMPILER_ROOT" \
  --work "$SV08_COMPILER_ROOT/tmp/markup-a" --build-venv /tmp/closure-backend \
  --backend-wheelhouse "$SV08_TASK_SCRATCH/backend-wheels" --execute
```

Repeat the wheel command with a fresh `markup-b` path. The compiler root must supply the pinned Python/compiler/backend environment. Preserve failing work. Source, installed backend bytes, compiler versions and selected output hashes are checked; a differing output is retained with a report and rejected. These commands require the applicable development execution authority for their disposable resources.

For packaging, create a separate wheelhouse with exactly the eleven selected runtime wheels: the ten unchanged supplier wheels and the new MarkupSafe wheel. Pass that wheelhouse and the rebuilt helper explicitly:

```sh
python3 scripts/package_klipper.py --work build/assigned-klipper-a \
  --wheelhouse "$SV08_TASK_SCRATCH/selected-wheelhouse" \
  --helper "$SV08_TASK_SCRATCH/helper-a/c_helper-aarch64.so" --execute
```

`assigned-klipper-a/rootfs` must be the assigned completed disposable baseline, with its `refresh-complete` marker and fresh application paths. Run a second assembly in a fresh workspace. The historical default helper/wheelhouse is intentionally preserved and fails the new selected hashes. Likewise, Moonraker's historical intake wheelhouse contains an obsolete streaming wheel: use an explicitly verified wheelhouse matching its current lock, not the intake directory by habit. Never mutate historical wheelhouses to make them match.

RAUC uses the existing `scripts/package_rauc.py`, pinned archive, exact project patch and recorded disposable compiler dependencies. Source-bound commands, toolchain metadata and the independent ARM64 match are in the evidence. Mainsail, Moonraker, KlipperScreen, streaming-form-data and Pycairo retain their matching existing proof; changing their sources, patches, locks or toolchain requires reassessment.

## License inventory

[The generated inventory](../../configs/host/source-license-inventory.json) records six selected applications, 49 unique runtime wheels, all 934 selected Mainsail production/build dependencies, the 284-package documented Debian baseline and 146 build-tool/package/backend records. Supplier wheels and distro binaries are explicitly distinct from project source builds. The documented baseline is not a claim about every package in an arbitrary final image or workstation.

`license_inventory.py` takes explicit local inputs and does not download, execute package installers or infer SPDX expressions. Its module documentation defines the input contract. The [licensing-repair JSON](../features/build-license-closure/licensing-repair.json) includes the current input manifest with logical roots `$CHECKOUT`, `$REFERENCE_CHECKOUT`, `$ORIGINAL_CANDIDATE`, `$ORIGINAL_EVIDENCE` and `$REPAIR_EVIDENCE`; replace only those roots with assigned retained/reconstructed resources, then run:

```sh
python3 scripts/license_inventory.py --inputs /assigned/inventory-inputs.json \
  --output /assigned/source-license-inventory.json
```

Inputs bind current configs, source identities, actual notices, artifacts, locks and rebuild receipts. NPM archives must match lock SRI, primary package name/version and copied notice bytes. Present notices cannot be omitted. Debian copyright links/texts and existing reviewed common-license references are checked without altering supplier files. Regenerate into a second output and compare bytes. An intentionally inspected missing declaration stays unresolved; it cannot substitute for missing evidence.

This is a factual inventory, not a legal compliance assessment. Sixty-nine NPM archives provide a supplier declaration without an embedded notice file. The original admission extension is now covered by the selected project AGPL-3.0-or-later grant and includes actual package notices. Its earlier undeclared-license observation is preserved in the original evidence; see the [licensing repair](../features/build-license-closure/licensing-repair.md). No upstream license is reassigned. Debian gzip's existing literal `GFDL-3` reference remains recorded as invalid while its shipped GFDL-1.3 text and prior review remain intact. License ownership/redistribution decisions require separate resolution before a compliance claim. Debian source-index availability does not assert source retrieval or rebuilding.
