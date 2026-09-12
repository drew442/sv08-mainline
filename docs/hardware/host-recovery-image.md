# Independent ARM64 recovery image

This offline candidate boots the installed GTK recovery service from its own
kernel, initramfs and complete Debian userspace with no A/B or data disks attached.
[ADR 0014](../decisions/0014-independent-compressed-recovery.md) defines the
read-only ext4 envelope and verified compressed `/usr` contract. The
[approved scope](../features/host-recovery-independent-image/proposal.md) preserves
512 MiB recovery within the 7,818,182,656-byte layout.

## Exact intake and assembly

The [binary lock](../../configs/host-os/recovery-packages.json) selects 284 packages
from Debian and Debian security snapshot `20260901T000000Z`: 222,909,108 archive
bytes and 745,582 KiB declared installed size. Actual sizing uses populated files,
not that declaration. APT resolved against an empty installed status for ARM64,
without recommendations; all archives agree with locked SHA-256, length and
Package/Version/Architecture control fields. Bootstrap unpack uses force-depends;
[Resolution/toolchain evidence](../../configs/host-os/recovery-resolution.json)
records the roots and repeat simulation. Final configuration enforces dependencies, every selected package must report
installed and `dpkg --audit` must be empty. ARM64 Python imports GTK, GDK, ATK,
Cairo, GLib and the actual runtime's standard library dependencies.

The [source inventory](../../configs/host-os/recovery-sources.json) maps every
binary to 176 exact Debian source versions and 572 archive URLs, sizes and hashes.
Signed InRelease verification authenticates retained Packages/Sources indexes.
Private intake evidence labels identify retained build evidence, not repository
relative links. Source archives are indexed; this delivery does not download or
rebuild them. Installed copyright and common-license texts are retained alongside
all runtime libraries, translations, fonts and documentation.

The [copyright inventory](../../configs/host-os/recovery-copyrights.json) and
[reference audit](../../configs/host-os/recovery-license-references.json) distinguish 95 sentence punctuation references
from one literal upstream discrepancy: gzip's copyright names `GFDL-3` at line 50,
while lines 42–47 specify GFDL 1.3 or later with no invariant sections. The image
retains the unmodified copyright and actual `GFDL-1.3` text, SHA-256
`110535522396708cea37c72a802c5e7e81391139f5f7985631c93ef242b206a4`.
No invented alias or rewritten upstream license hides this discrepancy.

## Reproduction and boundaries

Run from a clean checkout with the recorded host toolchain and ARM64 binfmt support.
Each command inspects unless `--execute` is supplied. Choose fresh ignored output
paths. Intake runs unprivileged; package assembly and filesystem creation run in
private mount/PID/network namespaces. No workstation package installation is used.

```sh
python3 scripts/recovery_image.py intake --work build/recovery-intake --execute
sudo -n unshare --mount --pid --net --fork python3 scripts/recovery_image.py assemble --intake build/recovery-intake --work build/recovery-assembly --execute
sudo -n unshare --mount --pid --net --fork python3 scripts/recovery_image.py build --assembly build/recovery-assembly --work build/recovery-image --execute
sudo -n unshare --mount --pid --net --fork python3 tests/recovery_filesystem.py --assembly build/recovery-assembly --build build/recovery-image --work build/recovery-inspection --execute
sudo -n unshare --mount --pid --net --fork python3 tests/recovery_vm.py --build build/recovery-image --work build/recovery-boot --seconds 120 --inputs --execute
```

Build performs a fresh SquashFS compression unless explicitly using the development
cache option. Acceptance repeats fresh compression. Assembly identity includes
root metadata, numeric ownership/modes, file bytes, symlink text, lstat extended
attributes (including ACLs/capabilities), and deterministic hardlink topology.
Packaging normalizes timestamps separately. Integration input hashes are captured before assembly/build
and checked at completion. Filesystem readback compares compressed userspace
and the physical envelope, including permissions and direct boot artifact bytes.

The VM uses QEMU `virt`, Cortex-A53, two emulated CPUs and 768 MiB RAM. It has only
the recovery disk, no host filesystem sharing and no NIC. A private Unix QMP socket
supports screenshots and input; it provides no guest shell or media authority.
The installed read-only report service records mounts, boot identity, memory,
service state and actual production controller status through the serial console.

Virtual touch uses QEMU 8.2.2 `virtio-multitouch-pci` and `InputMultiTouchEvent`,
which generate Linux ABS_MT_SLOT/TRACKING_ID/POSITION events and BTN_TOUCH with
INPUT_PROP_DIRECT. It is distinct from the USB tablet's absolute mouse events.
Primary source: [QEMU input implementation](https://raw.githubusercontent.com/qemu/qemu/v8.2.2/hw/input/virtio-input-hid.c)
and [QMP event schema](https://raw.githubusercontent.com/qemu/qemu/v8.2.2/qapi/ui.json),
revision v8.2.2, accessed 2026-09-12. Physical HDMI/touch-only validation remains
in the [canonical human tasks](host-os-tasks.md).

The existing production media provider remains unchanged and refuses unsupported
export, restore and slot operations. Diagnostics and review/cancel/apply for the existing Check
storage registry inspection work without creating a persistent registry. This does not establish
trusted premount composition, physical export, production owner/TLS provisioning,
H616 boot firmware/DTB/driver integration or a complete release capacity budget.

## Measured candidate and repeat

The [machine-readable receipt](../../configs/host-os/recovery-evidence.json) binds
one authoritative assembly (`build/recovery-assembly-v5`), candidate
(`build/recovery-final-v3`) and fresh repeat (`build/recovery-repeat-v3`). Earlier
exploratory images are not acceptance evidence. Generated images and screenshots
remain ignored; the receipt retains their hashes and exact source identities.

| Measurement | Authoritative result |
| --- | ---: |
| Recovery image capacity | 536,870,912 bytes |
| Populated compressed `/usr` | 224,436,224 bytes |
| Independent kernel | 37,660,608 bytes |
| Independent initramfs | 3,604,408 bytes |
| Free ext4 bytes | 230,875,136 (220.18 MiB) |
| Free ext4 inodes | 31,055 of 32,768 |
| Complete assembly regular-path bytes | 787,984,554 |
| Compressed userspace logical regular-path bytes | 740,135,601 |

Both images pass `e2fsck -fn`. Read-only filesystem inspection matches all 1,703
physical envelope metadata paths, with only mkfs's `lost+found` added. Compressed
userspace matches the source's full schema-2 identity. The setuid D-Bus helper
retains numeric owner/group `0:992`, mode `04754`; host group-name rendering is not
authoritative for candidate numeric identities. All source extended attributes
are empty. For 3,727 readback paths where SquashFS's attribute API reports
unsupported, comparison explicitly verifies the matching source set is empty;
unsupported does not generally mean no attributes existed.

The final candidate SHA-256 is
`98e4030b0902e877d912d9a627e481cd0e24dddeb81d118050e82e9869001a56`.
Fresh repeat compression produces byte-identical kernel, initramfs and compressed
`/usr`, and identical logical content/metadata. The full ext4 files differ in 108
4-KiB blocks, all within the first inode table (blocks 73–180). Across 1,702 inodes,
changed bytes are confined to inode ctime bytes 12–13 and checksum bytes
124–125/130–131. Envelope-copy ctime is the actual build time; access, modification
and creation timestamps remain normalized. No content, ownership, mode, hardlink,
xattr, allocation or other bytes differ. The [kernel inode layout](https://www.kernel.org/doc/html/latest/filesystems/ext4/inodes.html)
defines these fields (accessed 2026-09-12). No post-build mutation is used to hide
this explained nondeterminism.

## Actual boot, restart and refusals

Two sequential fresh QEMU processes attach only the unchanged read-only recovery
image. They report different boot IDs and successful installed display service,
no failed units, active D-Bus accessibility components, read-only root and `/usr`,
and no persistent registry. The console also reports optional libbpf/cgroup-BPF
features unavailable; this is retained separately from the empty failed-unit list
and does not establish board support. Startup takes 50.764 and 49.412 seconds respectively
in these emulated runs; this is not an H616 boot-time claim.

The harness waits, with a finite deadline, for the actual installed display/GUI
process report and AT-SPI registry readiness before injecting input. Screenshots
show Tab focusing Check storage, Shift-Tab returning focus, keyboard review with
Cancel default, Escape cancellation, mouse review and keyboard apply. Direct touch
Refresh/Check/Cancel/Check/Apply repeats the diagnostic journey. Apply performs the
existing registry inspection; it does not measure physical media health. The UI
leaves Check disabled until Refresh to prevent duplicate apply. Boot/restore/export
remain unavailable, with the missing verified media-policy reason displayed.

Eight actual early-boot cases refuse before the verified marker/UI: missing or
changed manifest, missing or changed compressed userspace, wrong filesystem UUID,
writable backing, a symlink compressed path, and a preassigned loop mapping. Each
uses a disposable owned copy, preserving the candidate. The loop case uses a
test-only initramfs wrapper around the byte-identical production gate; it assigns
read-only loop1 to `/spurious` at offset 0 with unlimited size, removes setup mounts,
then executes the unchanged gate. This is a negative-fixture mechanism, never an
installed media provider or production gate exception. The first seven refusal
receipts predate the positive-input readiness instrumentation; their unchanged
negative command/artifact/gate path and serial refusals are retained. The loop
case and both accepted positive journeys use the final readiness-aware harness.

## Resources and preservation

The completed authoritative assembly takes 7m12s and has a GNU time child
per-process RSS high-water of 288,192 KiB. An equivalent fresh assembly under the external sampler completes in 6m57s, with
a byte-identical completed schema-2 assembly record. Its sampled process-tree
summed RSS peak is 348,901,376 bytes; maximum additional workspace consumption is
990,949,376 bytes, including temporary generated files before cleanup. Its GNU
time child per-process RSS high-water is 285,032 KiB. The sampler observes zero
allocated data blocks in assembly tmpfs mounts; this excludes directory metadata,
kernel overhead and page cache and is not a zero-memory-cost claim. Fresh image
construction has a sampled
process-tree summed RSS peak of 269,500,416 bytes and consumes at most 621,223,936
additional workspace bytes in that run. The repeat's overlapping negative-fixture
creation affects its shared-filesystem low-water measurement; that figure is
explicitly labeled rather than attributed solely to compression.

The two final VM runs have sampled process-tree summed RSS peaks of 1,524,383,744
and 1,531,236,352 bytes on the workstation, including QEMU translation/graphics
costs. This is distinct from the guest's 768 MiB allocation. Guest meminfo and
service resource observations are retained in the receipt. Summed RSS may count
shared pages repeatedly and 250-ms sampling can miss transient peaks; it is not a
claim of exact total host memory accounting. Runtime tmpfs limits are explicit:
`/dev` 16 MiB/4,096 inodes, `/dev/shm` 32 MiB, `/run` 96 MiB, `/tmp` 64 MiB. The
complete root is never decompressed into RAM.

The source baseline's content/mode/owner fingerprint remains unchanged. Its
historical fingerprint did not include xattrs, hardlinks or root metadata; the
new completed assembly/build identities do. Workstation account/identity files
also match. The workstation's pre-existing unattended updater independently
changed libc/Python/wireless-regdb packages at 06:02:20–06:02:37 UTC on 2026-09-12,
so the earlier host dpkg-status hash does not match. The receipt records that
external event; authoritative assembly/build occurred afterward and their host
toolchain/library versions and hashes are recorded. This task installed no
workstation dependencies and did not contact the printer.

Assembly/build capture integration input hashes at entry and reject changes at
completion. Intake's standalone completion receipt currently hashes its lock at
completion without separately rejecting a concurrent lock replacement; tightening
that reporting edge is follow-up work. The authoritative assembly independently
validates the full captured lock, every archive/control field and completion
continuity, so this intake reporting limitation does not substitute for candidate
provenance.
