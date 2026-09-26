# Network eMMC one-shot protocol: QEMU evidence

Date: 2026-09-26 UTC. Feature: [network-emmc-one-shot](../features/network-emmc-one-shot/proposal.md).
Status: offline QEMU pass. No printer or physical block device was opened.

## Result

The guest consumed one durable job claim before opening its synthetic target.
The complete 7,818,182,656-byte nonbootable fixture was written to a disposable
32,000,000,000-byte regular-file-backed QEMU USB disk, flushed, read back in the
guest, then independently read back and inspected by the host harness. The source
and both readbacks matched SHA-256
`7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`.
The host verified the protective MBR, primary and backup GPT CRCs, disk GUID, and
all six partition names, identifiers, offsets and sizes. The backup GPT remains
at the reviewed 8 GB image extent.

The claim was bound to descriptor SHA-256
`22a060143dabff9d91f10a6da785efb10e62f7bd648b3f90c95da687ecbf8563` and job ID
`qemu-reimage-test-001`. Before acknowledgment, the claim service wrote the
154-byte consumed record with exclusive creation, `fsync` on the record and
containing directory, then removed and synced the arm marker. The guest made one
HTTP request over QEMU's isolated user network. The 41-minute full run measured
5.40 ms claim latency, 151,232 bytes current Python allocation increase, a
246,336-byte Python allocation peak, and 835,584 bytes process RSS increase.
The claim-state directory retained 154 bytes after completion.

A separate QEMU claim-only run returned the same bound descriptor and confirmed
`target_opened: false`. It measured 5.34 ms claim latency, 150,429 bytes current
Python allocation increase, 246,203-byte peak, and 823,296 bytes RSS increase.
The native tests separately prove one winner across 12 concurrent callers,
refusal after restart, refusal for missing/corrupt state or a changed descriptor,
and no replay after lost acknowledgment, sync failure, or interruption before
write, during write, at flush, or during readback. These faults leave the job
consumed or uncertain and never produce success.

The final receipt, sanitized to omit raw serial, is
[`host-network-emmc-one-shot-qemu-20260926.json`](host-network-emmc-one-shot-qemu-20260926.json).
Its `guest_serial_sha256` is
`338d80dd32502c6b702fb71b9de26038e1a63aff54aabefb95206690433469d4`. QEMU was
8.2.2 on Beelink; the ARM64 guest was limited to 2 GiB. The run used a private
network and mount namespace, read-only NFS source, at least 9 GB free scratch,
and the existing 75-minute host deadline. At completion the test directory
occupied 2.8 MB. No QEMU or temporary Ganesha service remained. An unrelated
pre-existing rpcbind process on Beelink was left untouched.

During bring-up, an early run safely stopped before claiming because its parser
rejected the newline ending `/proc/cmdline`. The claim-only run then passed after
the parser fix, followed by the full write/readback pass. The first run created
no claim and no target allocation. This failure and correction did not involve
hardware.

## Evidence boundary and next step

This demonstrates single-use sequencing and full-image byte transfer only in
QEMU. The source image is synthetic and nonbootable; the target identity is a
QEMU test serial. It does not test an H616 eMMC CID, a physical eMMC write, power
loss behavior, authenticated production admission, or printer boot. The claim
service and writer remain test-only and are absent from the production SD image
builder. A production network job service/trigger and live eMMC adapter still
need separately reviewed design and implementation.

H12 remains the one deduplicated physical commissioning task. Before it can run,
match the installed eMMC's live CID against the private evidence, bind the exact
commissioning image and target map to the real adapter, complete independent
high-consequence review, and authorize the exact write. The present diagnostic
still powers down after its read-only probe; its SD U-Boot loads the SD path and
does not establish automatic eMMC boot or fallback. Nothing here requests an
eMMC move, a printer boot, or a physical write.
