# Independent compiled-wheel rebuilds

2026-09-10. Offline ARM64 QEMU compiler and isolated application tests; no printer
access. [Build inputs and outputs](../../configs/host/compiled-source-wheels.json)
record source hashes, backend versions, compiler flags and canonical debug paths.

## Results

Pycairo 1.29.1 rebuilt in a fresh build environment with exactly the original
wheel SHA-256, `8766d812146248b9f34b549a148b309af763447659410ce01924b09e780cace0`.
Its existing runtime lock is unchanged. Source/build-tool hashes were checked
before use; pip ran with no index, no cache, no build isolation and no dependency
resolution, using the already reviewed source/backend inputs.

The first fresh streaming-form-data 2.1.0 build differed from the original wheel.
Only its extension module and wheel RECORD changed. DWARF inspection identified
the random pip extraction directory in `DW_AT_comp_dir`; ELF allocated sections
were identical apart from the build-ID note. The reproducible recipe now extracts
to a fixed source basename and uses GCC's supported prefix-map options. It keeps
the original Python CFLAGS, including `-g -O2`, rather than replacing optimization
and debugging settings. No source patch or Cython regeneration is involved.

Two independent source directories then produced identical wheels:
`b84023a8e49a3fcfe3f734702e61acd19fba88b261e3d4698a068b751148f66a`.
Their extension's allocated sections also match the original except for the
build-ID note; debug paths now begin `/usr/src/sv08-wheel-build/streaming-form-data`.
This establishes the recorded environment/recipe, not all possible toolchains.

## Reproduction

Use the separate completed Debian ARM64 compiler root and the hash-checked
setuptools 78.1.1 build venv described in [stack build inputs](host-stack-build.md).
The [rebuild command](../../scripts/build_streaming_wheel.py) validates source,
Python/backend/compiler versions and flags, refuses existing work, disables
resolver/cache use, and checks the result against the recorded wheel hash.
Default execution is inspection. For example:

```sh
sudo unshare --net --mount --propagation private \
  python3 scripts/build_streaming_wheel.py \
  --compiler-root build/python-builder-v1/rootfs \
  --source build/python-builder-v1/rootfs/tmp/moonraker-inputs/streaming_form_data-2.1.0.tar.gz \
  --build-venv /tmp/sv08-wheel-rebuild-v1/venv \
  --work-name streaming-fresh-build --execute
```

The compiler is Debian GCC 14.2.0-19 with Python 3.13.5. The venv parameter names
a path **inside** that compiler root. Its backend wheel must first be checked
against the build-input manifest. Source-date epochs and complete original CFLAGS
are in the manifest; prefix-map placeholders are resolved only for this fresh
work directory and build venv. Preserve source archives and build-tool wheels.

Private logs/results: `build/compiled-wheel-rebuild-v1.log`,
`build/streaming-deterministic-final.log`, and the compiler root's
`/tmp/sv08-wheel-source-v4` and `v5`. The documented runner uses `v6` in its
validation run. Initial flag experiments are not selected runtime artifacts.

## Packaged application validation

The Moonraker runtime lock now selects the reproducible streaming wheel. Fresh
package assemblies with new venvs produced identical
`sv08-moonraker_0.11.0+git985c1d0b-2_arm64.deb` packages:
`5bbc65c0441391837859c9131829b241f2a91a3f7e028221d1a5e8bd08f226e1`.
The Moonraker source pin and all other runtime wheel hashes are unchanged.

Builds used separate disposable OverlayFS uppers over the completed package
baseline, saving workstation space. This was a **build fixture**, not a change
to the OS persistence design. Existing baseline files were not modified. Mounts
were private and removed afterward; package outputs/reports remain in
`build/moonraker-repro-package-v1/` and `v2/`.

A further isolated overlay installed the new deb and checked its extension bytes
against the selected wheel. The real packaged API and browser then completed
initialization and a configuration-file upload/read/delete roundtrip with zero
uncaught exceptions. Klipper was absent and the network namespace had only
loopback. Evidence is in `build/moonraker-repro-api-v1/` and the
[public result](host-compiled-wheels-20260910.json). Earlier OS images and hardware
records retain their original package versions; this test does not rewrite them.

Primary source records, accessed 2026-09-10:
[streaming-form-data 2.1.0](https://pypi.org/project/streaming-form-data/2.1.0/),
[Pycairo 1.29.1](https://pypi.org/project/pycairo/1.29.1/), and the local hash-checked
source license files. Streaming-form-data uses MIT; Pycairo offers
LGPL-2.1-only OR MPL-1.1. Dependency/source/license manifests for the entire image
remain a separate release gate. Retire the wheel wrapper when the chosen
upstream/distro artifact provides the required reproducible ARM64 build.
