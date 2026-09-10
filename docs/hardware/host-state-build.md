# Host state, boot selection and signed-update tests

Work started 2026-09-09; continued 2026-09-10 UTC on the development workstation. No printer connection, MCU
write, eMMC write or physical board validation occurred. This extends the
[application build](host-stack-build.md). All images, test keys and raw logs are
ignored under `build/`; they must not be published as a printer release.

## Implemented integration

[Decision 0006](../decisions/0006-host-state-integration.md) describes the policy
and remaining gaps. `scripts/integrate_host_os.py` stages the runtime, explicit
systemd units, persistent SSH identity configuration, loopback Moonraker seed and
APT policy into a completed isolated rootfs copy. It defaults to inspection and
requires `deployable: false` plus six distinct explicit PARTUUID device paths.
It does not enable printer services or supply a printer configuration, bootloader,
DTB, recovery system, trusted production signing key or onboarding credentials.

Example, after making a fresh completed baseline copy under `build/`:

```sh
python3 scripts/integrate_host_os.py --work build/host-integration-v2 \
  --manifest build/host-integration-inputs/release.json
sudo python3 scripts/integrate_host_os.py --work build/host-integration-v2 \
  --manifest build/host-integration-inputs/release.json --execute
python3 -m unittest discover -s tests -q
sudo unshare --mount --propagation private python3 tests/host_mount_namespace.py
```

The manifest used here has random fixture UUIDs, not printer partition identities.
After staging, rebuild the initramfs with the target
`update-initramfs -u -k 6.12.107+deb13-arm64`; staging alone does not rebuild it.
The new hook prepares identity before PID 1. Debian's standard ext4 fsck hook is
selected explicitly because this image uses mount units instead of fstab entries.
The target's klibc mount utility needs `-o bind`, not util-linux's `--bind`.

The mount test really enforces immutable writes with `EROFS`, permits writable
root writes and shared user/config writes, keeps dpkg state slot-local, and checks
both mode transitions preserve customization status. Unit tests additionally cover
late state changes after staging, committed SQLite WAL, failed copies, rollback,
corrupt pending records, copied-file ownership and incorrect device identity.
Trial boots keep Klipper stopped until health confirmation is implemented.

Initial systemd verification found an ordering cycle through `systemd-sysusers`;
the unnecessary ordering edge was removed. Verification using the target's ARM64
systemd 257 succeeds; the workstation's older systemd 255 emits version-related
warnings on unrelated Debian units. Unit verification alone does not establish successful boot.

## Upstream tool builds

Exact archive URLs, commits and SHA-256 hashes are in
[the tool source record](../../configs/host-os/offline-tool-sources.json).
Archives are separate from the seven unchanged upstream submodules.

- U-Boot v2026.07, commit `ece349ade2973e220f524ce59e59711cc919263f`:
  `sandbox_defconfig`, EFI capsule authentication disabled because this test does
  not exercise EFI, and `BOOTMETH_RAUC_RESET_ALL_ZERO_TRIES` disabled. Exhausting
  both slots must reach recovery rather than endlessly replenish attempts.
- RAUC v1.13, commit `1183a396a2e10e92e428c396a510113edcd9037b`: built the initial
  signed bundle. Actual installation on workstation Linux `7.0.0-31-generic`
  failed before slot writes because this RAUC rejects dm-verity status `V -`.
- RAUC v1.15.2, commit `4fb7c798d6ae412344fb8f8d310d773046af3441`: replacement native
  test installer. Its upstream `src/dm.c:check_status` handles the newer format.
  This is an offline tool choice, not yet a pinned ARM64 image package.

Native RAUC uses Meson with `-Dtests=false -Dnetwork=true -Dstreaming=true`, then
Ninja. `.tarball-version` and `GIT_CEILING_DIRECTORIES` set to the archive parent
prevent the enclosing project Git version from leaking into RAUC's generated
version header. A clean rebuild was needed after discovering this in the first
build; the executed binaries report their upstream versions. U-Boot builds
out-of-tree with `O=` and the standard Makefile; no bundled installer was run.

Primary source references, accessed 2026-09-09:
[U-Boot RAUC boot method source](https://github.com/u-boot/u-boot/blob/ece349ade2973e220f524ce59e59711cc919263f/boot/bootmeth_rauc.c),
[RAUC dm-verity status parser](https://github.com/rauc/rauc/blob/4fb7c798d6ae412344fb8f8d310d773046af3441/src/dm.c),
[RAUC 1.15.2 release](https://github.com/rauc/rauc/releases/tag/v1.15.2).
The latter also fixes an overflow in large **plain** bundles; this project tests
and requires **verity** bundles and does not relax verification to bypass failure.

## U-Boot sandbox results

The actual sandbox executable reads all six partitions in the factory-capacity
[relocated GPT fixture](host-ab-layout.md), including their PARTUUIDs. A separate
copy has FAT boot partitions containing a dummy `boot.scr` that prints its slot
and root partition. The sandbox test DT enables fake `mmc10`, puts it first in
`bootdev-order` and adds the upstream RAUC boot method. `bootmeth order rauc`
followed by `bootflow scan -l`, `bootflow select 0`, `bootflow boot` exercises it.

| Input counters/order | Observed script | Saved counters |
| --- | --- | --- |
| B A; A=3, B=3 | `rauc.slot=B`, root partition 4 | A=3, B=2 |
| B A; A=3, B=0 | `rauc.slot=A`, root partition 2 | A=2, B=0 |
| B A; A=0, B=0 | No slot script | Both remain zero |

`env select FAT` and test-only `ENV_FAT_DEVICE_AND_PART="a:1"` enable actual
counter saving to the fake MMC's first FAT partition. U-Boot filesystem device
arguments use hexadecimal `a` for device 10. This environment placement is only a
test fixture: it is unsuitable for production because updating boot A would erase
it. Redundant production environment allocation and power-loss tests remain open.
Dummy scripts return, so successful marker cases subsequently report `EFAULT`;
they do not boot Linux. Raw logs are `build/uboot-ab-tests/*.log` and
`build/uboot-gpt-layout.log`.

The two `.cmd` files under `configs/host-os/` are integration templates. The board
port must supply verified device selection and load addresses. Neither template
is installed in a deployable image. Subsequent [raw-environment tests](host-environment-build.md)
exercise recovery-script dispatch; booting a recovery OS remains outstanding.

## Signed bundle and installer fixture

`build/rauc-bundle-v1/paired.raucb` contains the measured 2 GiB ext4 capacity
fixture and a 192 MiB dummy FAT boot image, signed with an ignored test-only key.
Its compatible string is deliberately `sv08-offline-test-only`. Signature
verification succeeds with its test certificate. The root and boot image hashes
in the signed manifest match their inputs. This is not a bootable release.

The following invokes a private D-Bus and native RAUC service, writing only four
new regular files beneath the specified new build directory:

```sh
sudo unshare --mount --propagation private python3 tests/rauc_file_install.py \
  --rauc build/rauc-native-v2/rauc \
  --bundle build/rauc-bundle-v1/paired.raucb \
  --keyring build/rauc-bundle-v1/keys/test.cert \
  --work build/rauc-install-v2 --execute
```

The v1.15.2 run passed: both inactive hashes matched, both active hashes were
unchanged, primary remained A, and B remained marked **bad** until explicit
activation. Separate untrusted-key, wrong-compatible, payload-corruption and signature-corruption
attempts each failed before changing any of the four slot files. The result/logs
are retained under `build/rauc-install-v4/`. This leaves activation as a distinct
operation; a coordinator must not assume installation makes B bootable.

Bundle size is 502,298,492 bytes (479.03 MiB), below the 1 GiB staging budget.
SHA-256: `06adf1217d4cc771293d13361efe7cce702566e7550e2410eb49ef2dad17cdef`.
This does not yet prove total worst-case data occupancy with user files and state.

The test uses raw file-backed slots and a test custom boot chooser. It must check
both inactive image hashes, preserve both active file hashes and preserve primary
A with `activate-installed=false`. This validates real RAUC installation, not
production ext4/vfat device handlers or the Linux U-Boot environment backend.
See the [remaining checklist](host-os-tasks.md) for integration and hardware gates.

The runtime also provides `sv08-state` and `sv08-package` commands. Mutations
default to inspection; for example `sv08-state policy --mode writable` only shows
the proposed operation. `--execute` belongs before the subcommand. Actual mode
application still requires a controlled reboot; the idle-aware UI/reboot
coordinator is outstanding. Package execution currently requires stopped services.

## Full ARM64 guest boot checks

The disposable `build/host-qemu-v1/disk.img` uses the same factory-capacity GPT,
Debian ARM64 kernel and staged root. QEMU boots it directly with its `virt` machine
and virtio storage; it bypasses the H616 boot chain and has no network or physical
USB passthrough. Boot B and recovery are not populated for this mode fixture.
Do not write it to a printer.

`tests/host_qemu_probe.py` is installed only in this disposable fixture, with a
temporary systemd service and explicit `--execute`. It refuses execution outside
a QEMU VM or against a deployable manifest. It checks real root write behavior,
config, PID 1 journal identity, hostname, SSH host key and customization persistence,
then powers off. The fixture service is not part of the normal integration stage.

Boot tests exposed and corrected missing initramfs utilities/fsck configuration,
late identity preparation, logind's writable linger directory and inappropriate
transient machine-ID commit in writable mode. The nginx default site is masked
until authorization/onboarding integration is ready. Persistent journals have a
64 MiB limit, with a 16 MiB runtime limit. These are observed integration fixes,
not evidence of Wi-Fi, HDMI, camera, MCU or printer compatibility.

The final three-boot sequence passed on 2026-09-10: immutable → writable →
immutable. The writable root edit remained present after the last boot, and the
slot remained marked customized. Config, machine ID, journal identity, changed
hostname and SSH host key all persisted; logind was active and no failed units
were reported. All three guests shut down normally. Logs are
`build/host-qemu-v1/boot-{0,1,2}-final.log`. The integrated 2 GiB root fixture passes
fsck; precise sizes and test results are in the
[evidence record](host-state-20260909.json).

These tests do not yet exercise a full kernel boot into B followed by rollback,
RAUC health confirmation, active-print admission or production environment writes.
