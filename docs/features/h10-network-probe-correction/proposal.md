# H10 network probe correction

## Problem and intended result

The 2026-09-26 supervised SD boot reached Linux and DHCP but failed to mount
the NFS root, so the eMMC probe did not run. The trace also shows Linux MMC host
numbering differs from the probe's hard-coded `mmc2` assumption. Correct the
existing approved diagnostic so its normal NFSv3/TCP mount path is tested and
the eMMC is discovered only beneath the exact H616 eMMC controller path,
independent of dynamic `mmcN` numbering.

## Bounded scope

- Keep the existing SD artifact, NFS-root architecture, eMMC offsets and
  read-only open/pread behavior.
- Correct and document Beelink rpcbind/mountd registration; test a default
  NFSv3/TCP mount without an explicit mountd port, including read-only refusal.
- Enumerate host/card/block directories beneath only
  `/sys/bus/platform/devices/4022000.mmc/mmc_host`, accept exactly one nominal
  32 GB MMC, and fail closed on ambiguity.
- Add host tests for the target under `mmc0`, an unrelated small SD under
  `mmc2`, and multiple matching MMC cards.
- Update H10 evidence to record the failed attempt and require a new independent
  high-consequence review before any physical retry.

No eMMC, SD, MCU or boot-policy write is in scope. This correction grants no
hardware authority.

## Acceptance checks

1. Focused C/Python tests demonstrate host-number-independent discovery,
   unrelated-card exclusion, and ambiguity rejection.
2. Static init builds with warnings as errors and its exact hash is recorded in
   the served manifest/composition receipt.
3. Beelink completes a default NFSv3/TCP read-only mount test without an
   explicit `mountport`; writing to the mount is refused.
4. The supervised physical failure is documented without claiming the probe ran
   or counters were read; another boot is blocked pending separate Sol review.
