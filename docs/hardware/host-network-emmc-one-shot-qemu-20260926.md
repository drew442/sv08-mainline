# Network eMMC one-shot protocol: QEMU evidence

Date: 2026-09-26 UTC. Feature: [network-emmc-one-shot](../features/network-emmc-one-shot/proposal.md).
Status: offline QEMU pass. No printer or physical block device was opened.

## Successful full-image path

The guest consumed one durable job claim before opening its synthetic target.
The complete 7,818,182,656-byte nonbootable fixture was written to a disposable
32,000,000,000-byte regular-file-backed QEMU USB disk, flushed, read back in the
guest, then independently read back and inspected by the host harness. Source,
guest readback, and independent host readback all matched SHA-256
`7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`. The host
verified the protective MBR, primary and backup GPT CRCs, disk GUID, and all six
partition names, identifiers, offsets and sizes. The backup GPT remains at the
reviewed 8 GB image extent.

The 42-minute ARM64 guest run used QEMU 8.2.2 on Beelink, a 2 GiB guest, a
private network and mount namespace, a read-only NFS source, at least 9 GB
scratch space, and the existing 75-minute timeout. Its 154-byte durable claim
was bound to descriptor SHA-256
`22a060143dabff9d91f10a6da785efb10e62f7bd648b3f90c95da687ecbf8563` and job ID
`qemu-reimage-test-001`. Claim latency was 4.94 ms; Python allocation increase
was 151,320 bytes, peak allocation was 246,336 bytes, and host RSS increase was
835,584 bytes. Guest serial SHA-256 was
`955f56a1e028474e1a02575ce793c4f9372ff51167840f06a8dd212d25030e3b`.

The successful full transfer executed writer and harness source at commit
`f44b887`. The submitted source head is `d916b23`; the intervening changes only
renamed the native claim-persistence test to remove its misleading simulated
phase-fault claim and guarded claim-server shutdown if setup failed before its
thread started. The current-head fault tests below exercise the new phase path.
The three current code hashes are listed in the JSON evidence.

The QEMU guest emitted three atomic page-allocation warnings from network worker
threads during the transfer. It did not report an OOM kill or NFS error; the
full guest and independent host readbacks, GPT checks, and success receipt all
passed. This is recorded as an emulation observation, not as proof that the
same warning or performance occurs on H616 hardware.

## Claim-only and interruption paths

A current-head QEMU claim-only run verified the descriptor and durable claim,
then powered off without opening the target (`target_opened: false`). Its claim
latency was 4.91 ms; persisted state was 154 bytes; Python allocation increase
was 150,597 bytes, peak allocation was 246,204 bytes, and host RSS increase was
827,392 bytes. Guest serial SHA-256 was
`4ecd2abd0b78406e6cd17c28112c432a491578af57d21aa982b4bc6ac76e1085`.

Four separate current-head QEMU runs injected terminal faults through the actual
ARM64 C writer after the server had durably consumed the claim:

| Injected point | Target observation | Claim replay | Success receipt | Guest serial SHA-256 |
| --- | --- | --- | --- | --- |
| Before first write | Target unchanged | HTTP 409 consumed | None | `2b804cb7b5f0ab44ee28c618d096eab272541f1ba6ad05a2a54fda04249c7d41` |
| After a real 1 MiB partial write | Prefix matches source | HTTP 409 consumed | None | `d380e054e804886e6ef4bf6b093ea577047f423e57cc45dba6fbf41ec40e1828` |
| After a real write and successful `fsync`/`BLKFLSBUF` | Prefix matches source | HTTP 409 consumed | None | `c9811dfc46f4518c35bb2319064150fc5e8d5b7d84c978f2712146138a47a1bb` |
| During readback after write and flush | Prefix matches source | HTTP 409 consumed | None | `2b3ab42dfcd4efeb8f10912a779c257f9f78c552dac524f6486d77ea649c2676` |

Each run ended through the guest's fail-closed power-off path. The harness
verified the phase-specific serial marker, no success/readback marker, durable
claim record, refused second claim, and the stated target-prefix condition.
This proves controlled phase handling in QEMU; it is not a physical power-cut
test. The service restart and lost-ack replay tests also passed independently.

The machine-readable receipt is
[`host-network-emmc-one-shot-qemu-20260926.json`](host-network-emmc-one-shot-qemu-20260926.json).
No QEMU or temporary Ganesha service remained after the runs. An unrelated
pre-existing rpcbind process on Beelink was left untouched.

## Evidence boundary and next step

This demonstrates single-use sequencing and whole-image transfer only in QEMU.
The source image is synthetic and nonbootable; the target identity is a QEMU
test serial. It does not test an H616 eMMC CID, a physical eMMC write, real
power-loss behavior, authenticated production admission, or printer boot. The
claim service and writer remain test-only and are absent from the production SD
image builder. A production network job service/trigger and live eMMC adapter
still need separately reviewed design and implementation.

H12 remains the one deduplicated physical commissioning task. Before it can run,
match the installed eMMC's live CID against private evidence, bind the exact
commissioning image and target map to the real adapter, complete independent
high-consequence review, and authorize the exact write. The current diagnostic
still powers down after its read-only probe; SD U-Boot loads the SD path and does
not establish automatic eMMC boot or fallback. Nothing here requests an eMMC
move, printer boot, or physical write.
