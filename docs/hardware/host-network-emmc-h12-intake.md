# H12 installed-eMMC intake and writer handoff

This is the coordinator's order of work for the single [H12 session](coordinated-human-tasks.md).
The [offline live-staging result](host-network-emmc-live-stage-offline-20260927.md)
does not establish the identity or writable state of the installed eMMC. The
factory module stays stored and the spare stays installed; no USB writer or
media move is requested.

1. Wait for the owner to confirm printer power, USB-serial and wired Ethernet
   state. The serial connection itself powers the host, so arm receive-only
   Beelink capture before any disconnection/reconnection or cold boot. Check
   that Beelink can reach the printer's reserved `192.168.1.141` address.
2. Collect a **read-only** live inventory over SSH: the unique card beneath
   `4022000.mmc`, MMC type and CID, `/dev/mmcblk0` capacity and device number,
   kernel partition-five PARTUUID/device number, GPT and both redundant
   environment records. Record the exact board compatible and whether p5 is
   mounted, at what path and with what options. If it is unmounted, do not
   mount it read-write during intake. Inspect the original recovery script,
   available p5 space and current A/B state only when the filesystem has been
   safely mounted read-only with journal replay disabled or an equivalent
   existing read-only mount has been verified. Keep CID and raw captures under
   ignored `local/`, with only redacted hashes in public reports.
3. Build a private canonical target policy from that **current** inventory and
   the reviewed v5 image map. The live staging CLI's default `inspect` requires
   this policy: it cannot discover a CID before the policy exists. Use it to
   re-admit the same eMMC after policy creation. Treat any identity, GPT,
   mount-source or policy mismatch as a stop, not an invitation to edit the
   policy to fit an unexpected board.
4. Recheck the exact v5 raw source on Beelink. The compressed archive alone is
   not an NFS source for the RAM writer. Prepare a regular raw source file with
   the manifest's 7,818,182,656 bytes and SHA-256
   `ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`;
   the trusted writer reads it as `image.bin` at the root of the selected NFS
   export. Verify that export is read-only and independent of the target. Check the
   one-shot claim service and exact job/signing keys without exposing them in
   the repository. Any source or service that is unavailable stops the handoff.
5. Build and review the physical `h12-attended-candidate` FIT, signed job,
   target policy, original-script hash, source hash, size and recovery-space
   budget. Confirm that the running host can execute the staging adapter and
   its required tools from persistent storage; the current v5 image predates
   this adapter. Preserve an independent SD rescue path. No fixture key or
   synthetic policy may enter this candidate.
6. Immediately before each eMMC/boot-policy action, obtain the required
   independent GPT-6 Sol high-consequence review of the exact target,
   artifact, operation, stop conditions and recovery. Execute stage, arm and
   activate separately, recording each journal and serial result. First test
   fallback/FIT handoff without whole-device target open (`urh-04`). Only a
   separate attended full write, flush, readback, GPT check and next boot can
   satisfy `urh-05`. A partial or uncertain state stops; never retry or rearm
   automatically.

The owner need only restore physical connectivity and report the power/serial
state. The coordinator handles the commands, artifact checks and reviews. The
offline test results and H10's dated eMMC observation cannot replace a fresh
live intake.

## Beelink source preparation, 2026-09-27

The reviewed v5 `.xz` archive on Beelink expanded to 7,818,182,656 bytes with
SHA-256 `ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.
A newly staged sparse raw file was fsynced and then separately read back with
the same hash. It occupies 3,135,639,552 physical bytes. The read-only raw
file is hard-linked as `/srv/sv08-sd-nfs/image.bin`, so that export name uses
no second image allocation. Beelink's kernel NFS export lists
`/srv/sv08-sd-nfs` as read-only with root squash for `192.168.1.141` and
Beelink's own `192.168.1.136` address. A fresh Beelink-local NFSv3/TCP mount
read all 7,818,182,656 bytes and reproduced the hash; an attempted file
creation was refused. The mount was removed after the check. Beelink had
7,552,151,552 bytes free after staging, measured before the NFS read.

This establishes source bytes and one local export path, not printer reachability
or a physical RAM-writer boot. Recheck service, export, file hash and free space
at H12; an earlier local pass cannot substitute for the live network path.

The same v5 raw image's root-A partition was mounted from a read-only loop with
ext4 journal replay disabled. It contains Python 3, `fw_setenv`, `dumpimage`,
`findmnt`, `ip`, OpenSSL, `mount` and `unshare`. The image does not contain the
new live adapter or an apparent recovery mount point; inspect the running host
before choosing its persistent deployment path and recovery mount. A 32,909-byte
source-only adapter archive was prepared from commit `2c806c5`, tested by
importing it from an isolated extraction and checking the reviewed physical v5
layout, and copied to Beelink at
`/home/drew/sv08-h12/h12-stage-adapter-2c806c5.tar.gz`. Its SHA-256 is
`739868bdbe4dc7eb445d2dc6872e38ccf3add1aee9f7b2928bbbf38e1af5e9d6`.
It contains no private policy, keys, signed job, FIT or image. It has **not**
been installed on the printer or executed against its eMMC.
