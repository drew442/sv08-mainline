# ARM64 RAUC package and partition installation

Recorded 2026-09-10. This is offline build/VM evidence, not printer compatibility
or a deployable image. [Decision 0007](../decisions/0007-rauc-package-candidate.md)
records the reason for evaluating the upstream package instead of retaining
Debian's RAUC 1.13 unchanged. The distro ARM64 kernel remains selected.

## Package build

[Package inputs](../../configs/host-os/rauc-package.json) pin upstream RAUC 1.15.2,
commit `4fb7c798d6ae412344fb8f8d310d773046af3441`, its archive SHA-256 and source
epoch. The configuration's candidate status is its selection status; subsequent
evidence is recorded here. No upstream source patch or bundled installer is used.

Prepare the documented compiler root from the Debian/security snapshots at
`20260901T000000Z`, installing the build dependencies listed in that JSON. Keep
this separate from the runtime image. Supply the archive from the recorded URL;
the build tool verifies its hash and does not download floating inputs.

```sh
python3 scripts/package_rauc.py \
  --archive build/ab-source-intake/rauc-1.15.2.tar.gz \
  --builder build/python-builder-v1 --work build/rauc-arm64-v3
sudo python3 scripts/package_rauc.py \
  --archive build/ab-source-intake/rauc-1.15.2.tar.gz \
  --builder build/python-builder-v1 --work build/rauc-arm64-v3 --execute
```

Use a fresh output directory each time. Meson uses release mode, JSON, network
and streaming support, explicit `/usr/lib/systemd/{system,catalog}` locations,
compiler path remapping and the pinned source epoch. Network capability in RAUC
does not enable the planned future Internet update policy. `dpkg-shlibdeps`
derives shared-library requirements; the package also declares external runtime
tools. Builds retain source provenance, upstream licensing and complete compiler
package versions. The script does not enable or start the updater.

Two clean source builds (`build/rauc-arm64-v3` and `v4`), using different build
paths in the same isolated compiler root, produced identical packages:

- Package: `rauc_1.15.2-0sv08.1_arm64.deb`.
- SHA-256: `964b0636cc13a431aaab428b13d2c28d067c82f95894e6bc85b41cebed4abd42`.
- Executed version: `rauc 1.15.2`.

This is not an independently reconstructed compiler environment. The
[evidence record](host-rauc-20260910.json) retains all compiler package versions,
binary hash and runtime results. An intermediate package put journal catalogs in
a multiarch directory; the final recipe sets the standard systemd catalog path.

## Isolated runtime installation

The package was installed into a fresh copy of the complete host stack before
staging operating-mode integration. Dependency resolution added `liblzo2-2` and
`squashfs-tools`; no application package was removed. A subsequent rebuild used
the same package version with the corrected catalog path before VM testing.
The image builder's daemon-start prohibition now applies only while the system
is unbooted. On a booted system, the supported writable package workflow can
start ordinary services; printer service start gates still enforce their lock.

The fresh integrated root uses fixture release `0.1.0-offline.3` with explicit
fixture PARTUUIDs and `deployable: false`. It includes the same pinned application
payloads and Debian kernel `6.12.107+deb13-arm64`. Its 2 GiB ext4 filesystem passes
fsck and has 659,808,256 free bytes, including 21,471,232 reserved bytes.
Package caches were cleaned before integration; this differs from the earlier
conservative capacity fixture. Full image release assembly remains outstanding.

## Actual inactive-partition test

[The guest probe](../../tests/host_qemu_rauc.py) refuses execution unless explicitly
requested inside QEMU, on a non-deployable image, with disk serial
`SV08-QEMU-DISPOSABLE`. It verifies the active root/data identities, requires both
inactive targets to be unmounted and checks their sizes against the signed images.
The VM has no network or physical USB passthrough.

The virtual disk is exactly 7,818,182,656 bytes, using the six-partition factory
layout. This test uses actual `ext4` and `vfat` RAUC handlers writing virtual B
partitions; the earlier workstation test used raw regular-file handlers. A
private D-Bus and a test custom boot chooser isolate it from the ordinary system
bus. The boot chooser is still a fixture, not the Linux U-Boot environment backend.

The signed verity bundle and public test certificate are placed under
`/data/fixture`; the signing key stays outside the guest. The updater verifies the
bundle with the test-only compatibility string and installs without activation.
Results on the actual Debian ARM64 kernel:

- Both active A partition hashes remained unchanged.
- Both B partition hashes matched the signed images exactly.
- Primary stayed A; B remained marked bad pending explicit activation.
- The staged bundle occupied 502,298,492 bytes.
- The data filesystem still had **1,931,620,352 available bytes**, above the
  512 MiB reserve. Installation did not require expanding the root image into data.
- RAUC and the guest shut down normally.

Logs/results remain in `build/host-qemu-rauc-v1/`. QEMU boots the kernel directly;
this test does not validate H616 firmware, automatic boot selection, health
confirmation, recovery or printing. B contains the signed capacity fixture and
is not activated or claimed to boot. Required hardware tests remain in the
[completion checklist](host-os-tasks.md).

## Package workflow fixture

`tests/fixtures/qemu-proof/` defines a harmless package containing a marker file
and a service that touches a runtime marker. Build it with:

```sh
dpkg-deb --root-owner-group --build tests/fixtures/qemu-proof \
  build/host-qemu-rauc-v1/sv08-qemu-proof.deb
```

Place it at `/data/fixture/sv08-qemu-proof.deb` only in the disposable mode-test
image. `tests/host_qemu_probe.py --execute --with-package` verifies immutable
refusal, writable installation through the real wrapper/APT/dpkg hook, service
activation and preservation of the package record/files after returning to
immutable. The temporary guest service selects `sv08.test=modes`; the partition
installer fixture selects `sv08.test=rauc`. Neither test service is staged by the
normal image integration tool. Live-print admission is still unimplemented.

The corrected package fixture passed all three boots on 2026-09-10. Immutable
installation was refused; writable installation succeeded through the actual
APT hook, and its ordinary systemd service started. The installed file, dpkg
version and customization status survived the subsequent immutable boot. The
first fixture omitted service enablement, so Debian correctly declined to start
its disabled service; adding normal maintainer-script enablement corrected the
fixture. Final logs are `build/host-qemu-rauc-v1/mode-{0,1,2}-v2.log`.
