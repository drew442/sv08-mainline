# Synthetic CID-to-descriptor QEMU validation

Date: 2026-09-26. Scope: disposable ARM64 QEMU guest with a regular-file-backed
32,000,000,000-byte virtual USB disk. This is offline fixture evidence, not a
printer eMMC write or an H616 MMC topology measurement.

## Combined identity path

The NFS test root supplies a deliberately synthetic MMC inventory at
`/synthetic-mmc/mmc0/mmc0:0001/block/mmcblk0`. Its separate, compiled-in
expected CID is `00000000000000000000000000000001`, the type is `MMC`, the
capacity is 62,500,000 512-byte sectors, and its `dev` file is `8:0`.
That last file is an explicit **test adapter**: QEMU attaches the same
regular-file-backed virtual disk as USB storage, where Linux exposes it as
`/dev/sda` with major/minor `8:0`. The writer admits exactly one synthetic
MMC candidate, reads this adapter's device number, then opens `/dev/sda` once.
It compares `fstat`'s `st_rdev` with both the admitted adapter number and
`/sys/block/sda/dev`. After hashing the source, it repeats CID/inventory and
device-number checks at the write boundary. The same opened descriptor is
used for write, flush, and complete readback. The network job JSON contains no
CID field or override. A changed fixture card path is refused because this
adapter intentionally accepts only its fixed test topology.

The adapter proves that the **QEMU test** connects a checked synthetic CID to
the descriptor receiving bytes. It does not prove that an H616 kernel exposes
the physical eMMC CID, card path, and opened block descriptor this way. It
cannot eliminate every hotplug or kernel mapping race. A production writer is
still absent, and H12 retains live private CID comparison, exact
artifact/target/recovery review, independent high-consequence review, and
physical authorization.

## Focused checks

`PYTHONPATH=tests python3 -m unittest tests.test_sd_network_emmc_write
tests.test_sd_network_cid_admission tests.test_emmc_job
tests.test_sd_network_env_probe tests.test_sd_network_image -q` passed 36
tests. The native synthetic adapter checks matching and changed CID, wrong
type/capacity, malformed and mismatched device numbers, renamed and ambiguous
cards. The opened-device selftest checks strict sysfs parsing and block-node
type. `aarch64-linux-gnu-gcc -static -Os -D_FORTIFY_SOURCE=2 -Wall -Wextra
-Werror` compiled the guest writer. The production SD/NFS builder and
diagnostic remain unchanged.

## QEMU results

The bounded full run used Beelink, `sudo unshare -n -m`, QEMU 8.2.2,
`aarch64-linux-gnu-gcc` 13.3.0, `sgdisk` 1.0.10, and host kernel
`7.0.0-31-generic`. Its fresh regular-file-backed target was
32,000,000,000 bytes; the synthetic image was 7,818,182,656 bytes. The
source and complete guest readback SHA-256 were both
`7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`.
The host independently read back and hashed all image bytes. Both GPT CRCs,
disk GUID, and all six partition records matched. The durable claim was
consumed before the first target open, and a post-run claim-state replay
returned status 409 `CONSUMED`. Guest serial ended in `SV08_QEMU_REIMAGE_PASS`; host exit
status was zero. Wall time was 44:11.84, maximum host-run RSS 2,309,768 KiB,
and remote scratch remained above 10.7 GB free. Nine guest `GFP_ATOMIC`
allocation warnings appeared, with no OOM or NFS error in the serial log.

The full result JSON SHA-256 is
`711507ab2d2ade46ddc3120f3c15950597a824429e7d3d254155750112b5d4cc`;
the guest serial SHA-256 is
`fd6ac7f01cf38a54d8764adc7ca192b1183ac237e4ea1bf4ede8189480914745`.
The actual staged C writer and Python harness SHA-256 values were
`f74c80317dfa6f40d0999b8398ce46468aa9ce92cef2e86f787131edeb631de0`
and `396fb5337e3052e48fc0c59080f26508c033cf45d23981bec8505dc4e0db60d5`;
both matched the local sources.

The wrong-CID QEMU run refused with
`SV08_QEMU_REIMAGE_REFUSED_SYNTHETIC_MMC` in 1:26.30. Its claim was
consumed, replay returned 409, no success receipt appeared, and the target
remained unchanged with zero allocated 512-byte blocks. Its result JSON and
guest serial SHA-256 values were
`0acb6ba2e83d18ad476774f7f748948b55bf822b3138de1a6df58ad4336d4437`
and `c72a4f90c6d381742d86f8b2f55f9bb3b9327725f422b737e421d42e4c1d6d28`.
An earlier wrong-CID guest emitted the correct refusal but the host evaluator
incorrectly demanded a full-readback receipt for that identity-fault mode;
this was corrected and the run above is the counted result.

The partial-write QEMU run reached the prewrite recheck, wrote a real 1 MiB
source prefix to the target, then stopped at
`SV08_QEMU_REIMAGE_INJECTED_PARTIAL_WRITE` in 17:11.89. The host confirmed
the target prefix matches source, the claim stayed consumed, replay returned
409, and there was no success receipt or automatic retry. Its result JSON
SHA-256 was
`c8e5db759906a403179ffa7349dec6a9a8e210cd9af8bc58e0cb63c4a2cc9223`;
guest serial SHA-256 was
`cb5961cb3a0f2eba7f168cf54a9a65b8bb1979be156ec4282dc26dd5a3710768`.
The target had 160 allocated 512-byte blocks after the stop; this is a
partially written, unusable virtual disk by design.
