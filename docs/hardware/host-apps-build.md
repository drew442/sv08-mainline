# New host application packaging

Date: 2026-09-09. Status: Klipper package validated offline; no activation.
Target: Debian trixie arm64 baseline for test-sv08-01. PCB revisions remain
unknown. No printer connection, hardware writes, heat or motion in this work.

The [package tool](../../scripts/package_klipper.py) combines the
[reviewed inputs](../../configs/apps/klipper.json) into a native `.deb`.
Klipper is pinned to `f0892d82b0f1c1228454f09eb508eddde2250f4b`, matching the
selected MCU builds. It archives only the upstream runtime and license, adds the
previously built ARM64 helper, and installs eleven hash-locked Python wheels in
a venv at its final absolute path. It does not run upstream installers or patch
upstream source. The package contains no printer configuration, service units,
maintainer scripts or MCU firmware.

This custom integration fills the gap between upstream source and the project's
matched host/MCU release composition. Retire it when a maintained upstream or
distro package can provide that composition. Source/helper build provenance is
in the [MCU build record](test-sv08-01-mcu-build.md); Python wheel provenance is
in the [host integration record](test-sv08-01-host-integration.md). Embedded
upstream COPYING and wheel license metadata are retained. This is an internal
packaging candidate, not a published distribution release.

## Reproduce

First complete all stages of the [Debian baseline](host-ab-build.md). Requires
its Linux/ARM64 chroot tooling plus `dpkg-deb`, and the reviewed helper and wheel
artifacts identified in the package profile. Use a fresh isolated copy; the tool
refuses existing application/package paths. Default invocation verifies inputs
and prints a dry-run; `--execute` builds only inside the workstation directory.

```sh
sudo cp -a --reflink=auto build/host-ab-baseline-v1 build/host-apps-v1
python3 scripts/package_klipper.py --work build/host-apps-v1
sudo python3 scripts/package_klipper.py --work build/host-apps-v1 --execute
python3 -m unittest discover -s tests -v
```

Outputs remain ignored under `build/host-apps-v1/`: package, staged payload and
manifest. The build removes the scratch source/venv it created from the copied
rootfs after success. Installing the resulting package for validation is a
separate operation; never install this experimental package on the printer.
Failed builds require a fresh copy, not an automatic destructive retry.

Upstream chelper checks timestamps to decide whether compilation is needed.
The package normalizes source and prebuilt helper timestamps to the pinned Git
commit time so loading the helper does not need a compiler. Changes to source,
helper, lock or installation paths require a new reviewed package profile.

## Completed checks

The [sanitized result](host-apps-20260909.json) records the exact package and
input hashes. The `.deb` is 5,702,162 bytes, SHA-256
`a418eeddfbb95b0b1d228ce19961ae1fde0d6879e9784c51d5f63c0c4c6608cf`.
Repeated archive assembly of the same normalized payload was byte-identical;
this does **not** establish an independent clean rebuild of all dependencies.

Installation through dpkg into the isolated baseline succeeded, with APT
checking dependencies. The installed package ran the existing dual-MCU
sensor-only configuration in Klipper file-output mode under ARM64 QEMU, using
matching dictionaries for both MCUs. Both configured successfully and the
process exited normally. The helper also loaded as unprivileged UID/GID 65534
without a compiler. These checks do not test physical MCU communication or an
immutable mounted OS. Package control metadata contains only `control`.

After installation, package-state inspection passed with 477 packages,
1,280,905,934 apparent root bytes (1,221.57 MiB) and 74,531,314 boot bytes
(71.08 MiB). This leaves about 314 MiB below the 1,536 MiB root-content budget.
Measurements include baseline package indexes; filesystem metadata, recovery,
update staging and user data still require separate capacity tests.

## Remaining work

- Moonraker, Mainsail and KlipperScreen packaging is now in the
  [complete stack build](host-stack-build.md); full deployment/staging capacity
  and activation still need validation.
- Integrate the distro ustreamer candidate and the retained camera settings.
- Add coordinated service activation, persistent configuration/state and the
  immutable/writable operating modes from [decision 0004](../decisions/0004-os-operating-modes.md).
- Build and validate the board boot chain, A/B selection, rollback and recovery.
- When hardware is available, perform sensor-only host/MCU integration before
  any full-printer commissioning. No human action is needed for the next offline
  application packaging work.
