# Running SD recovery host test

This separately named, nondeployable composition completes the owner's running
recovery GUI and SSH development journey. It reuses the independent recovery
GTK/systemd userspace and pinned 6.18.51 board kernel. Physical SD boot, display,
touch, Ethernet and controller behavior remain pending; VM results cannot certify
those functions. The ordinary finite SD/NFS diagnostic and release/A/B builders
are unchanged. This composer is retired when supported release recovery includes
SD deployment.

## Sources and build

[The composer](../../scripts/build_sd_recovery_host.py) accepts only the authorized
512 MiB v5 recovery partition, SHA-256
`c83975508e1cafca51e23c6ad9e19408fa01b5d35be583b39a38c5b13ad2345c`.
It reads ext4 through `debugfs`, without mounting or opening physical devices.
The coordinator supplies bounded package-listed public `/usr` files, symlinks,
Debian dependency/version metadata, public owner/group namespace and license notices from the pinned offline
host root. Exact manifest hashes, import content/ownership/mode and differing overlay hashes
are retained in the composition receipt; no private host configuration or SSH
keys are imported. The supplemental sudo package uses its upstream public PAM
conffiles. Kernel/DT hashes match
[the SD source pins](../../configs/host-os/sv08-sd-network-inputs.json).
Existing notices under `/usr/share/doc` remain in compressed userspace.

On the authorized regular-file build sandbox, run inspection first:

```sh
sudo python3 scripts/build_sd_recovery_host.py \
  --source /home/drew/sv08-sd-recovery-build/source-recovery.ext4 \
  --packages /home/drew/sv08-sd-recovery-build/ssh-installed-payload-manifest.json \
  --additional-packages /home/drew/sv08-sd-recovery-build/sudo-installed-payload-manifest.json \
  --owner-mapping /home/drew/sv08-sd-recovery-build/payload-owner-mapping.json \
  --sudo-pam /home/drew/sv08-sd-recovery-build/pam-sudo \
  --sudo-i-pam /home/drew/sv08-sd-recovery-build/pam-sudo-i \
  --public-key /home/drew/sv08-sd-recovery-build/development-authorized-key.pub \
  --work /home/drew/sv08-sd-recovery-build/owner-candidate
```

Add `--execute` to create fresh regular files. Source/work symlinks, block inputs,
input/output overlaps, altered source hashes and reused output paths refuse.
The extracted payload directories must be sibling `ssh-installed-payload` and
`sudo-installed-payload`. The builder defaults to inspection, never downloads or
runs package installers, and never writes SD/eMMC/MCU devices. It requires 3 GiB free for a fresh build or 1.5 GiB for a hash-checked userspace cache
reuse and checks a 3,500 MiB additional allocated build budget. Zstd level 10 uses two workers
and a 256 MiB compression memory limit. The root remains within the accepted
512 MiB recovery allocation; the explicit test disk is 704 MiB. No release or
factory 8 GB layout requirement changes.

`--reuse <completed-build>` reuses hash-verified compressed userspace only when
all package manifests agree. This reduces owner-only/configuration rebuild space.
`--test-public-key` adds an explicit synthetic authentication fixture and marks
that candidate test-only. **Omit it for the owner-only physical candidate.**

The loader must be freshly compiled using the existing pinned SD source,
configuration and patches with this build's exact `boot.cmd`, `boot/boot.scr` and
`loader-default.env`; the loader's compiled script hash makes an old loader
incompatible. Its receipt binds `deployable:false`, `boot_script_sha256`,
`environment_sha256`, `loader_sha256`, `config_filename` and `config_sha256`.
The assembler validates the existing SD-only configuration checks:

```sh
python3 scripts/build_sd_recovery_host.py assemble \
  --build /home/drew/sv08-sd-recovery-build/owner-candidate \
  --loader /home/drew/sv08-sd-recovery-build/loader.bin \
  --loader-receipt /home/drew/sv08-sd-recovery-build/loader-receipt.json \
  --output /home/drew/sv08-sd-recovery-build/owner-sd.img
```

Add `--execute` only for regular-file composition. Loader placement at byte 8192,
relocated GPT sector 4096, boot partition at 16 MiB and recovery partition at 144 MiB
preserve the existing loader separation. Receipt and final image hashes remain in
ignored build storage. A physical writer, target identity and reviewed write/readback
are separate coordinator operations.

## Runtime and trust

The gate requires a unique SD PARTUUID
`deaf981d-7441-428c-bf43-ce40bca6ca65`, partition index 2, exact 512 MiB capacity,
filesystem UUID `27ea34a6-fb05-4814-aaee-251071577ae1`, boot manifest digest and
compressed userspace hash. It verifies configuration-file and envelope-symlink
inventories before normal init, sets only the selected root partition read-only,
checks ioctl/sysfs readback, and mounts ext4 `ro,noload`. Incorrect or ambiguous
identity and corrupted content refuse before `switch_root`. No `/dev/mmcblkN`
controller mapping is assumed. These are corruption/admission checks, not a
secure-boot assertion.

Normal systemd remains running. The existing GTK recovery display is independent
of DHCP success; it reports missing state honestly and does not initialize a
persistent registry. The eMMC recovery media policy/provider are removed and
preparer/private-media units masked, so this test does not enable production
restore, export or boot selection. Printer, update, boot-health and installer
units are masked. `/run` 96 MiB, `/tmp` 64 MiB and `/dev/shm` 32 MiB are bounded
volatile mounts; `/var` state uses existing volatile symlinks. The early 180-second
watchdog is canceled before handoff.

The named `recovery` account accepts the supplied owner public key only; root,
password and keyboard-interactive SSH login are disabled. Its upstream sudo
configuration deliberately permits remote administration after key authentication.
That capability does not authorize media or hardware writes; those remain separate
reviewed coordinator steps. No shared password or owner private key is shipped.
Upstream networkd provides wired IPv4 DHCP, without DNS/NTP/hostname changes.

Each fresh boot generates an Ed25519 SSH host key in tmpfs and prints its public
SHA-256 fingerprint on the console. Verify that fingerprint before enrollment;
remove/re-enroll the previous development hostname's known-host entry after each
fresh boot. Restarting sshd within one boot preserves that key. Persistent host
identity is intentionally absent from this disposable medium.

## Focused offline acceptance

```sh
python3 -m unittest discover -s tests -p test_sd_recovery_host.py
python3 tests/sd_recovery_host_vm.py \
  --build /home/drew/sv08-sd-recovery-build/fixture-candidate \
  --work /home/drew/sv08-sd-recovery-build/vm-test \
  --test-key /home/drew/sv08-sd-recovery-build/test-client-key --execute
```

The VM uses the pinned Debian 6.12.107 kernel instead of the H616 kernel, 768 MiB
RAM, and identical composed root, initramfs/gate, GTK and SSH bytes. Its synthetic
key is exclusively an offline fixture. It tests two fresh boots, 210-second first-boot and 30-second restart
observations of running services, GUI keyboard review/cancel screenshots, SSH/sudo success,
unauthorized-key/password refusal, console fingerprint matching, volatile writes,
root-write refusal as root, partition ioctl/mount protection and source preservation. A separate no-NIC boot proves the local GUI remains usable without DHCP. Negative boots exercise wrong hash,
wrong partition index and corrupted compressed userspace. Source checks alone and
older GUI evidence are insufficient; inspect the current `run.json` and screenshots.
The coordinator owns independent verification, physical evidence and human queue
updates. Baseline eMMC, rollback, heater protections and printer-idle requirements
remain separate.

## Offline result, 2026-09-29

Implementation source was frozen by the coordinator at `cbf79b3`. Seven focused
unit checks passed. The complete final VM run exited zero using
`--observe 30 --seconds 300`: both fresh boots rendered GTK, accepted keyboard
review/cancel, authenticated the named account, executed `sudo -n id -u`, rejected
unauthorized keys and passwords, and preserved root protection and volatile writes.
The final service observations lasted 33.68 and 33.25 seconds. A separate boot
with `-nic none` rendered the same usable local interface. All three boots reported
no failed units and no persistent registry. Missing factory state is expected here;
the existing UI reports it and keeps production operations unavailable.

The gate refused changed envelope binding (35 seconds), wrong partition index
(20 seconds), and changed compressed userspace (56 seconds) before normal init.
The whole disposable VM disk and original recovery root hashes were unchanged.
The earlier first-boot run completed a 210-second observation, with authenticated
SSH still available at kernel uptime 401.49 seconds. Its second-boot SSH readiness
probe later timed out; that partial run supplies only sustained-runtime evidence,
not final GUI/restart acceptance. The final run supplies the latter. The normal
recovery init/watchdog cleanup bytes were unchanged between these runs.

Bounded logs, JSON, package manifests, owner composition/loader receipts, exact
builder snapshots and actual screenshots are in ignored coordinator evidence:
`local/sd-recovery-host/implementation-evidence-v2.tar.gz`. SHA-256:
`c43486670546781ae54e2e6b847f4928aa1c6eb692442b7a87c77810dfeb9fdc`.
The final `host-vm-final/run.json` SHA-256 is
`8ba0558755fce7e48b2fb6d9952e41a1bde62fd3d179a8edda9a0fd6e95302dd`;
the explicitly partial sustained evidence SHA-256 is
`6cf2c030008b041c7d19f12e85f375952eedf35297c1ca0d0e5b1279f2badbc5`.

The owner-only composition contains no synthetic authorized key. Its `/etc`
inventory differs from the final fixture only in `sd-host-authorized_keys` and
the corresponding checksum inventory. Both use compressed userspace SHA-256
`ab8a0e8dd48a112f4c95e3b8cec43e62b424b230fc5195400af47269e2db2537`.
The owner root is 536,870,912 bytes; the assembled regular test disk is
738,197,504 bytes, SHA-256
`2b0a6fa177515652722b53c0a7f306c3fb452c84b1af1ffa4dc01ab5c8ed0040`.
The owner composition receipt SHA-256 is
`91410e5ce1475c984115c6b1f964d764ea67d0e5ddf2538210917428f97ae2c8`.
Configuration binding means its gate/initramfs hashes deliberately differ from
the fixture; these artifacts are separately recorded rather than asserted identical.

Installed public runtime imports include OpenSSH `1:10.0p1-7+deb13u4` and sudo
`1.9.16p2-3+deb13u2`, with exact dependency metadata in receipts. Baseline
`sysvinit-utils 3.14-4` supplies `lsb-base`; imported `perl-base` supplies
`perlapi-5.40.0`. Shared license notice mappings retain `libgcc-s1` through
`gcc-14-base`, `libncursesw6` through `libtinfo6`, and the server/SFTP OpenSSH
packages through `openssh-client`. The composed target's ELF loader resolved
sshd, sshd-session, ssh-keygen, networkd and sudo successfully.

The VM substitutes pinned Debian kernel `6.12.107+deb13-arm64` for the unchanged
physical H616 kernel and uses emulated input/display/network. It does not exercise
the compiled SD loader or certify physical peripherals. Startup resource reports
show about 734 MB usable RAM and no swap within the 768 MiB VM setting. Physical
resource usage remains pending. Sudo prints a nonfatal hostname-resolution warning
in this isolated configuration while privileged commands succeed. No physical
media, eMMC, MCU, printer or boot-policy operation was performed. Independent
verification and any physical trial remain coordinator decisions.

## Resource evidence and physical dependency

The retained fresh v8 composition reports 1,032,187,904 bytes as the maximum
sampled allocated work size and source preservation; its preflight log records
5,712,080,896 bytes free. The v9 reused composition reports 713,228,288 bytes.
The older fresh builder did not sample immediately after compression, so this
sampled maximum is not a continuous peak measurement. The committed builder adds
that checkpoint. Fresh/reuse logs and complete receipts are retained under
`local/sd-recovery-host/resource-evidence/`; no extra build was run to recreate
these measurements. Compression uses two workers and 256 MiB memory; the bounded
build and VM resource evidence is distinct from physical runtime usage.

[H13 in the coordinated human queue](coordinated-human-tasks.md) records the
pending reviewed SD write/readback, one SD movement and captured host-only boot.
Its physical result is not part of this offline delivery acceptance.

## Attended SD reimage candidate (H12, 2026-10-03)

The new SD-only display drop-in selects
[the native screen](../../runtime/sv08_sd_reimage_ui.py) and
[the backend](../../runtime/sv08_sd_reimage.py). This replaces the generic export
screen only in this composition; other recovery and A/B mechanisms are unchanged.
The screen has no automatic write/reboot and no device-path entry. Review checks
are integrated into the normal Yes/No flow. Default No, Escape and dialog close
cancel; refresh does not write. Each invocation accepts only one answer. Failure
reports that the installed image may be unusable; keep SD and restart manually.
Whole-image replacement includes image-contained user data and environment. There
is no preservation or atomic rollback promise. Only the accepted image range is
written; eMMC boot partitions and storage beyond that range are excluded.

Coordinator prepares `/run/sv08/sd-reimage.json` before opening Review, containing
`source` (absolute regular image path on an independently backed read-only mount),
`size` (positive exact bytes), `sha256` (accepted lowercase digest), `target`
(measured whole user-area device), `dev_t` (`major:minor`), `cid` (measured sysfs
CID) and `controller` (resolved parent of `/sys/class/block/<target>/device`).
These production identities are unknown until actual admission; no example device
number or CID is a physical fact. No credentials, private backups or raw captures
are needed by this screen. Source mounting is separate coordinator preparation,
not a discovery/upload/network feature. A read-only independent ext4 source is the
prescribed installed fixture mechanism; NFS can be supplied only with its mount
closure confirmed separately. No image is staged in RAM or tmpfs.

Linux admission requires the verified recovery gate, unique controller/CID,
opened dev_t, sufficient capacity, independent read-only source and unused target.
It checks mounted devices/partitions, device-mapper ancestry, loop backing files,
holders and swap. Unknown block ancestry refuses. The held exclusive target and
source descriptors survive review. Immediately after Yes admission runs again.
The writer uses fixed 1 MiB buffers, short-I/O loops and a hash of transferred
bytes. It fsyncs, invalidates block cache with BLKFLSBUF, and hashes full image-range
readback. Any transfer/flush/cache/readback failure terminates without retry.
Regular targets are admitted only by explicitly constructed test fixtures.

Composition receipts bind exact backend/UI/drop-in input hashes and the buffer
bound. Compressed `/usr` reuse requires these hashes to match; old receipts or
changed runtime/drop-in bytes require a fresh userspace build. The 512 MiB root,
96/64/32 MiB volatile mounts, kernel/DT/loader pins and printer-service masks are
retained. New installed capacity and memory/storage observations remain pending.
The earlier results above remain historical evidence for the previous UI.

Focused commands (put all temporary output in the assigned scratch directory):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_sd_reimage.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_sd_recovery_host.py
PYTHONDONTWRITEBYTECODE=1 xvfb-run -a /usr/bin/python3 tests/sd_reimage_gtk.py --work "$SCRATCH/gtk"
python3 tests/sd_reimage_vm.py --build "$BUILD" --work "$SCRATCH/vm" --test-key "$TEST_KEY"
```

The [installed driver](../../tests/sd_reimage_vm.py) defaults to inspection.
Coordinator adds `--execute` only on a separately budgeted build/VM host. It uses
768 MiB RAM, the pinned Debian 6.12.107 VM kernel, independent virtual SD and two
8 MiB ext4 fixtures (read-only source and separate writable file target). It first
checks actual production service wiring and installed hashes, then temporarily
runs the explicit [GTK driver](../../tests/sd_reimage_gtk.py) through that installed
display service. Native XTest keyboard and pointer activation cover refusal/No,
Escape/close, Yes/write/full readback and relaunch, checking actual resulting bytes.
The production service is restored and relaunched without configuration and must
not write. Mount closure, source/SD preservation and memory/storage output are
recorded in `run.json`. XTest is test instrumentation, not a new runtime dependency;
its existing installed library availability must be confirmed in that run.

This driver has not yet been executed on the new installed ARM64 composition.
It substitutes virtio storage and explicit file-fixture target admission for
physical MMC identity; it cannot establish physical compatibility. Pending delivery
checks are fresh composition, installed execution and independent full-diff/hash
verification. Current measured source/target, exact-operation review, attendance,
physical full readback and observed manual normal boot remain coordinator-owned.
