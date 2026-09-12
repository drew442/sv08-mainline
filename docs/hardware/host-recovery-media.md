# Verified pre-mounted recovery export

2026-09-12. Offline implementation and disposable filesystem evidence for the
[approved feature](../features/recovery-media-export/proposal.md), extending
[the archive exporter](host-recovery-export.md). No printer, Beelink, network,
physical USB medium, private backup or upstream checkout was accessed. Test printer
01's host PCB revision remains unknown; no hardware acceptance is claimed.

The installed GTK entry now constructs [the media provider](../../runtime/sv08_recovery_media.py).
A verified configuration enables **Save user data** through its existing chooser,
review and apply controls. Missing, malformed, untrusted or mismatched inputs leave
export disabled with a displayed reason; registry diagnostics remain available.
The complete configured data filesystem is exported, while its `sv08/` registry
is read only for diagnostics. A damaged registry does not prevent export.

## Supported preparation contract

This provider inspects already prepared mounts. It does not discover arbitrary
devices, mount, repair, replay journals, set block flags, stop writers, eject,
restore, select boot slots or enable services. No production policy, per-boot
context or guessed target identity is shipped. The independent recovery image and
its trusted preparer must still be assembled and reviewed before activation.

Production supports simple physical disks and partitions, an ext4 recovery root
and source, and FAT destinations. Device mapper, MD, multipath/holders, loop devices,
overlay roots, missing stable identities and other unknown storage stacks refuse.
The following are separate prerequisites and observations:

| Item | Required evidence and validation |
| --- | --- |
| Reviewed image policy | Root-owned `/etc/sv08/recovery-media-policy.json` on the actual read-only recovery root, with trusted non-writable ancestors and no symlinks. It identifies the independently reviewed image manifest, exact recovery/source filesystem UUIDs, physical identities, partition number/start/size, and every system medium, including unmounted A/B media. Inventory completeness is a reviewed profile/preparer responsibility. |
| Actual recovery root | `/` must be the whole filesystem of the identified ext4 block mount, read-only at VFS, superblock and entire-disk levels. `/etc/sv08/recovery-image.json` must be on that filesystem and match the reviewed raw-byte SHA-256. Exactly one kernel argument `sv08.recovery=<that digest>` must identify the boot selection. A legacy display marker, label, configured role or device number alone grants nothing. |
| Per-boot preparation | Root-owned `/run/sv08-recovery/media-context.json`, beneath a root-owned mode-0700 directory, binds the policy's canonical JSON fingerprint and the measured boot ID, PID/mount namespaces, process root, complete mount table, directory identities, filesystem UUIDs and block topology. Expected values come from the trusted preparer, never the chooser. |
| Namespace and writers | The UI shares PID 1's root and PID/mount namespaces. Proc must expose all tasks without `hidepid` or a subset, and all userspace tasks must share those namespaces. Kernel tasks identified by `PF_KTHREAD` are exempt. Mount propagation must be private; unknown/overmounted paths refuse. The immutable recovery closure must contain only reviewed participants obeying the shared admission protocol. |
| Source preservation | Both source VFS and filesystem-superblock options must be read-only, with ext4 `noload`/`norecovery`; the selected partition and its whole underlying medium must already be block-read-only. Bind subtrees, aliases and submounts refuse. A read-only bind over a writable backing filesystem is insufficient. |
| Destination | An exact writable FAT mount on a kernel-reported removable disk, with stable physical identity and disk sequence, separated from recovery, source and all reviewed system media. Shared known identity attributes also exclude a system medium when another device path exposes additional attributes. Aliases, duplicate destination media and submounts refuse. |

The policy uses `format_version: 1`, `kind: independent-recovery`, protocol
`sv08-recovery-media-v1` and writer model
`reviewed-recovery-only; all-media-mutators-use-MediaLease`. `recovery` and `source`
contain `stable`, `partition`, `start`, `sectors` and `filesystem_uuid`;
`system_media` contains the reviewed stable identities of all protected media.
`image_manifest_sha256` hashes the manifest bytes. Context fields are
`format_version`, `protocol`, `policy_sha256`, `source`, `destinations` and
`expected`. Each destination has an internal selection ID, a label and an exact
mount path. `expected` is the provider's complete measured snapshot under admission.
These are a developer contract, not enabled example configuration.

Before the first source mount, preservation preparation must prevent writers and
block writes and suppress ext4 journal replay. Mounting ext4 with `ro` alone can
replay its journal. The provider cannot prove that earlier preparation preserved
the disk; retain preparation evidence and backups. It refuses inadequate current
conditions instead of changing them. The fixture hashes the source image before
and after all export/failure tests to check this preservation directly.

## Shared admission and publication

Every participating export, premount, media-change and future ejection/restore
operation must acquire `MediaLease` at the fixed
`/run/sv08-recovery/media.lock`. The mode-0600 root-owned file is never unlinked or
replaced. It is an exclusive, non-blocking process lock; a competing operation
gets a useful refusal. A lease alone supplies no hardware authority. Production
does not configure an alternative lock path.

The reviewed fingerprint includes actual mount IDs, namespace/root identity,
filesystem UUIDs, sysfs ancestry/inodes, stable physical IDs, partition geometry
and the kernel disk sequence. Thus device-number reuse is insufficient to preserve
a review. Review performs no archive write. Apply repeats inspection and binds
the reviewed media fingerprint into the export plan. Under exclusive admission,
the exporter checks again before writing, before no-replace publication, and after
directory fsync. The lease remains held during writing, full readback verification,
publication and directory fsync. Identity failure removes this operation's partial;
a detected failure after rename also attempts to remove only its new archive.

This is a cooperative protocol within an independently reviewed recovery closure.
It does not constrain arbitrary privileged software that changes namespaces, block
flags, raw media or the lock file. The provider checks the stated kernel conditions;
it cannot attest the absence of future hostile root processes. Physical removal or
power loss can prevent cleanup or persistence, so a complete-looking file after
such a failure still needs explicit verification. Hardware power-loss behavior
remains untested.

## Offline evidence and reproduction

Final provider SHA-256:
`c4db9d201f3479200b875193d34e37f0283facf64b3e4eda9ef02f92440a4c46`.
The implementation and tests use no network or target hardware.

```sh
python3 -m unittest discover -s tests -p 'test_recovery_media.py'
python3 -m unittest discover -s tests -p 'test_export.py'
python3 -m unittest discover -s tests -p 'test_stage_admin_ui.py'
python3 -m unittest discover -s tests -p 'test_admin*.py'
python3 -m unittest discover -s tests -p 'test_host_integration.py'
xvfb-run -a /usr/bin/python3 tests/recovery_gtk.py
xvfb-run -a /usr/bin/python3 tests/recovery_export_gtk.py
sudo unshare --mount --pid --fork --propagation private \
  /usr/bin/python3 tests/recovery_media_mounts.py \
  --work build/recovery-media-new --execute
```

The 40 targeted Python tests and both existing GTK regressions passed. The new
[real mount fixture](../../tests/recovery_media_mounts.py) also passed using five
64 MiB disposable images, private mount/PID namespaces, actual ext4/FAT mounts,
GTK under Xvfb and the actual controller/export/provider path. It checks 352 MiB
free space before setup, detaches only its own mounts/loops, and removes successful
disposable images while retaining its JSON result. Inspection without `--execute`
creates nothing; execution outside the documented namespace launcher refuses.

The fixture's explicit exception identifies a marked disposable recovery root and
loop backing files under this checkout's `build/`. It records the actual process
root/namespace but substitutes that marked ext4 root for production `/` and accepts
only its identified loop media. It does not establish an independent recovery OS
boot: GTK and Python still come from the workstation. The production entry accepts
neither the fixture policy kind nor fixture loop/root exceptions. All archive,
lease, mount, block-read-only, identity and preservation checks remain shared.

| Test | Result and evidence class |
| --- | --- |
| GTK selection, review cancellation, apply | Actual chooser cancel and review cancel created no archive. Apply produced a 10,240-byte verified archive containing the damaged registry and fixture configuration. |
| Preservation | Complete source/recovery image SHA-256 values were unchanged. Existing destination text and older `.partial` bytes were preserved; no test failure added a completed archive. |
| Exclusion | An actual competing process using `MediaLease` was refused, including probes during publication and directory fsync. Fixture mount preparation uses that same lease implementation. |
| Read-only bind and aliases | Actual RO bind over a mounted writable ext4 filesystem, extra source alias, source submount and a second userspace mount namespace all refused. |
| Removal/replacement | Actual lazy FAT unmount after archive verification prevented publication and released admission. Reattaching the same loop number with the same FAT UUID but a different backing file/disk sequence invalidated review. |
| Additional negative branches | Controlled kernel-observation doubles verify inconsistent VFS/superblock options, writable source whole medium, non-removable and same-system destinations, and a disk-sequence change during execution. Unit positive controls distinguish RO ordinary A/B/workstation identity and boot-token refusals from simple writable-root refusals. Identified loop media without the fixture exception refuse as unsupported production topology. |
| Configuration and staging | Missing/mismatched provider sources refuse before staging. Malformed configuration tests cannot reach admission. File validation has a valid-file control; actual permission and symlink behavior is checked with ownership/ancestor observations isolated in the unit test. |

The retained final fixture result is `build/recovery-media-v6/result.json`.
Its archive SHA-256 was
`12b54bb132c7d10908db6ba7594312d8d3b120408a76e977bd7ba9d81f34a806`.
Generated archives/images and machine-specific context are not committed.

The actual staged non-fixture `main()` was also rendered under Xvfb. This harness
uses private tmpfs `/etc` and `/run`, without touching installed trust files:

```sh
sudo unshare --mount --propagation private \
  /usr/bin/python3 tests/recovery_media_entry.py \
  --runtime build/media-staging-final-recovery/rootfs/usr/lib/sv08
```

Absent, malformed, untrusted and structurally invalid inputs each displayed their
specific diagnostic, disabled **Save user data**, exposed no destinations and kept
**Check storage** enabled. This used the staged entry's ordinary no-argument branch,
without an injected adapter or `--fixture`. Empty private `/etc` caused expected
Xvfb `awk`/fontconfig warnings; legacy GTK runs reported an absent AT-SPI bus. These
tests do not validate the final font/accessibility/input closure.

Workstation inputs: Python package `3.12.3-0ubuntu2.1`, GTK
`3.24.41-4ubuntu1.3`, PyGObject `3.48.2-1`, util-linux/libblkid
`2.39.3-9ubuntu6.6`, dosfstools `4.2-1.1build1`, e2fsprogs
`1.47.0-2.4~exp1ubuntu4.1`, Xvfb `2:21.1.12-1ubuntu1.6`. These are test
tools, not a new target-image package selection.

## Size, integration and remaining acceptance

Staging the same base runtime/assets at `f7a3d53` and the final implementation into
fresh isolated roots produced:

| UI payload | Before | After | Increase |
| --- | ---: | ---: | ---: |
| Host assets/helpers | 60,190 bytes | 84,465 bytes | 24,275 bytes |
| Recovery assets/helpers | 42,631 bytes | 66,906 bytes | 24,275 bytes |

The provider itself is 22,925 bytes. `integrate_host_os.py` already copies every
runtime module; UI staging now requires and hashes this provider with the matching
runtime. Recovery dependency inputs add one direct package, `util-linux`, for the
exact-node read-only `blkid -p` probe (which uses libblkid). No Python dependency or
host package is added. This is an input change; incremental target package closure
and installed footprint have not been resolved or measured. Payload measurements
exclude Python, GTK, X11, kernel, firmware and their full dependency closure.

Keep complete **512 MiB recovery closure** and **8 GB image-capacity acceptance**
open. The [canonical human checklist](host-os-tasks.md#human-and-powered-printer-tasks)
still requires a reviewed bootable recovery candidate, named-profile identities,
actual removable-media discovery/removal, physical touch/keyboard/mouse interaction,
attended failures and power-loss/recovery evidence. Independent image assembly,
trusted premount integration, progress, safe ejection, signed restore and boot
selection remain incomplete. Offline admission does not satisfy physical acceptance.

This original adapter fills the project-specific preserved-data/media admission
gap under [decision 0010](../decisions/0010-host-administration-and-recovery-ui.md).
Retire it when an upstream recovery service supplies equivalent reviewed identity,
source preservation, shared exclusion and verified publication semantics.
Primary references, consulted 2026-09-12: [Linux ext4 mount semantics](https://docs.kernel.org/admin-guide/ext4.html),
[mountinfo's VFS/superblock distinction](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html),
local `/usr/share/man/man8/blkid.8.gz` from util-linux `2.39.3-9ubuntu6.6`,
and `include/linux/sched.h:1749` in local Linux headers `6.17.0-35-generic`
for `PF_KTHREAD`. No downloaded revision is described as target compatibility.
