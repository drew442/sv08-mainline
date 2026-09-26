# Disposable SD/NFS whole-image writer prototype

Date: 2026-09-26. Decision: [0018](../decisions/0018-network-emmc-reimage.md).
Scope: offline ARM64 QEMU, synthetic regular files only. This is a separate
whole-image recovery experiment from signed A/B OS updates. It has no production
writer and does not change the existing read-only SD/NFS diagnostic.

The [prototype guest writer](../../tests/fixtures/sd-network-root/emmc_image_writer.c)
is compiled only by the [QEMU harness](../../tests/host_qemu_sd_network_emmc_write.py)
as a temporary `/sd-network-init` in a private NFS export. The original
[diagnostic init](../../tests/fixtures/sd-network-root/init.c) and
[SD image builder](../../scripts/build_sd_network_image.py) remain read-only and
do not include this writer. The Linux root and source image are on a read-only
NFS mount; the destination is a distinct QEMU USB mass-storage device backed by one
disposable regular file opened by the host harness. The guest requires the exact
`/dev/sda` path, its ancestor USB serial `SV08_QEMU_REIMAGE_TEST_ONLY`, no
second SCSI disk, and an exact 32,000,000,000-byte
capacity before opening the source or writing. The host refuses block devices,
symlinks, reused work directories, target substitutions, extra target candidates,
source/target overlap, and paths outside the assigned directory.

The source is deliberately **nonbootable synthetic data**, with a marker at the
would-be SPL location. It has the factory-sized 7,818,182,656-byte image extent,
the 16 MiB leading reserve, two redundant-environment reserves, six A/B,
recovery and data partition boundaries, and its backup GPT at the end of that
image extent. It is not a copy of the private printer image. The complete image
hash is pinned as
`7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`.
The synthetic GPT disk GUID is
`8aae17d2-09b3-47ab-8e35-8e91e63cf2b0`. Partition GUIDs and exact
boundaries are pinned in the harness. The larger 32 GB target intentionally
retains the 8 GB image's backup GPT at the image boundary; this prototype does
not expand the data partition or move the GPT to the physical end.

The guest hashes the complete source before writing and again while writing,
then flushes the destination, reopens it, and hashes the complete readback. The
host independently hashes the same complete target extent and validates the
protective MBR, both GPT header/array CRCs, disk GUID and every one of the six
partition names, numbers, GUIDs, offsets and sizes. `result.json` appears only
after all checks pass. Any refusal, short read/write, timeout, flush failure,
readback failure or hash/GPT mismatch yields no success receipt and an explicit
`FAILED` marker; a partly written virtual target is treated as uncertain.

The local low-cost checks are:

```sh
PYTHONPATH=tests python3 -m unittest test_sd_network_emmc_write -q
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror -o /tmp/sv08-emmc-image-writer tests/fixtures/sd-network-root/emmc_image_writer.c
python3 -m py_compile tests/host_qemu_sd_network_emmc_write.py
```

## Completed disposable run

On 2026-09-26, the final Beelink `run-006` QEMU 8.2.2 test passed under
`sudo unshare -n -m`. The kernel/initramfs were the previously verified
SD/NFS QEMU composition. The guest mounted its NFS root read-only, identified
only the 32,000,000,000-byte QEMU USB disk with the pinned serial, and reported
exactly 7,818,182,656 source, write and readback bytes. Both guest SHA-256
values and the independent host full readback SHA-256 matched the pinned
synthetic image hash above. Host inspection accepted the protective MBR,
primary and backup GPT CRCs and all six pinned partition records. The final
receipt is `qemu-only-pass`; it does not report a physical printer operation.

The exact sanitized receipt is committed as
[`host-sd-network-emmc-reimage-qemu-20260926.json`](host-sd-network-emmc-reimage-qemu-20260926.json);
its SHA-256 matches the original Beelink `result.json` at
`/home/drew/sv08-qemu-reimage-pilot/run-006/`. The guest `serial.log` has SHA-256
`be2e353f190263976d80dd0f67487c631769bab19b903b247a6c7a7bf5b5bc3b`.
The compiled static ARM64 writer has SHA-256
`605e1f0e5a78c20df3037cd6cf19d9a91f8a2cd234dfbc3cc0ffd3f325224d4e`.
The 7.8 GB source and 32 GB virtual target remained sparse regular files,
occupying 192 and 3,744 512-byte blocks respectively; the whole run directory
occupied 2.7 MB, and Beelink still had about 11 GB free. No `FAILED` marker
remained after the successful run. The guest logged five transient
`GFP_ATOMIC` page-allocation warnings while moving data through emulated USB
networking. Traffic advanced monotonically; the guest's full hash and host's
independent full hash both passed. These warnings are a QEMU stress limitation,
not evidence that physical H616 memory or eMMC writes are reliable.

Earlier disposable attempts refused a missing virtio block identity or stopped
before any write while fixing QEMU fixture memory and root-mount admission.
Their virtual target files had zero allocated blocks and no success receipt;
none used a printer or a host block device. Ten focused Python/native tests pass,
including short read/write, flush/timeout, wrong target/substitution,
truncated/changed source, GPT damage and uncertain-readback refusal.

For a full QEMU run, use an existing verified SD/NFS composition directory
containing `boot/Image`, `boot/initrd.img`, `boot.cmd` and `composition.json`.
Use a fresh private scratch directory on a host with at least 9 GB disk free
and 3 GiB available RAM. QEMU itself is capped at 2 GiB guest RAM. Supply a
local extracted NFS Ganesha/rpcbind package tree. The command runs only in a
private network and mount namespace; the QEMU guest gets a 75-minute host
limit and a 70-minute guest limit. For example, with paths supplied by the
assigned integration worker:

```sh
sudo unshare -n -m -- python3 tests/host_qemu_sd_network_emmc_write.py \
  --work /private-scratch/sv08-qemu-reimage-001 \
  --sd-work /private-scratch/verified-sd-composition \
  --package-root /private-scratch/extracted-nfs-packages/root --execute
```

The full run can logically read the 7.8 GB source three times and the target
twice, so its duration depends on NFS and storage throughput. The two image
files have 39,818,182,656 bytes of apparent capacity, but remain sparse;
zero-detection/unmap is requested for the virtual target. The 9 GB free-space
gate covers a worst-case 7.8 GB target extent plus margin. Stop if actual
scratch allocation or time exceeds the bound. Never use the printer's eMMC,
factory capture or a host block-device path for this test.

QEMU starts the Linux kernel and initramfs directly. It does not emulate H616
Boot ROM, SPL, U-Boot SD priority, real eMMC write protection, USB serial power,
or the printer's board/controller identity. Existing H09/H10 evidence shows only
a supervised physical SD/NFS boot and read-only eMMC environment probe. A
physical whole-eMMC write remains behind H12: an exact board/module and image
map, a recoverable boot path, independent high-consequence review and a separate
authorized hardware operation are required. This record cannot establish a
deployable image, data preservation on a whole-image rewrite, or printer boot.
