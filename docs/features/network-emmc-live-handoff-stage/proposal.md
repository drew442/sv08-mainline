# network-emmc-live-handoff-stage: Stage the recovery writer on the installed eMMC

Kind: improvement. Author: root/coordinator. Date: 2026-09-27.

## Problem and evidence

The approved [recovery handoff](../network-emmc-unattended-recovery-handoff/proposal.md)
and its [offline result](../../design/unattended-emmc-reimage-handoff.md) prove
ordered staging and a full writer journey only on disposable regular-file and
loop media. `scripts/stage_h616_recovery_handoff.py` explicitly rejects a live
block device. The printer cannot yet enter the writer without manually moving
media. H10 measured one eMMC under `4022000.mmc`, but that dated observation
is not current target admission; the current CID and mounted recovery device
have not been compared. The printer is not reachable over Ethernet at the time
of this proposal.

## Intended outcome

Provide a running-host stage tool whose default action reports a **read-only**
admission result. It must bind the exact signed target policy to a single
opened eMMC descriptor, current controller/card CID, MMC type, capacity and
device number, six-partition GPT and partition-five ext4 mount. A distinct,
explicitly invoked staging path may then preserve the original recovery
script, install the reviewed FIT/wrapper and journal the transition. A separate
explicit arm step must verify both redundant environment copies before a final
activation step publishes the one-shot marker. No automatic rearm or retry may
occur. The before/after result is a reviewed live-capable backend for the
already approved recovery handoff, with physical use still pending H12.

## Scope and alternatives

Reuse the signed job, target policy, artifact checks, controller and CID rules,
GPT inspector, marker-last sequence and one-shot claim already developed for
the RAM writer. The custom gap is the running host's binding of mounted
recovery and raw boot-environment writes to the same admitted eMMC. Prefer a
stable open descriptor to a fresh untrusted path lookup at write time. Keep
inspection, stage, arm and activation separately callable; default to
inspection. A live write-capable command must require an explicit operation,
reviewed artifact hashes and a new H12 high-consequence review immediately
before use. Synthetic fixtures must never authorize a physical action.

The implementation may use a small adapter around the existing offline
stager, but must not weaken its regular-file test boundary or the trusted RAM
writer's independent target admission. Do not alter the normal A/B updater,
SD diagnostic, factory eMMC or MCU firmware. The original recovery UI and SD
rescue path remain independent. Revisit or retire this adapter when the host
updater owns the transaction through a tested supported interface. This
proposal neither creates an unattended schedule nor claims a supported release.

## Acceptance and task split

| Check | Environment | Evidence required |
| --- | --- | --- |
| `lhs-01` | Offline | Read-only live admission rejects wrong/ambiguous CID, controller, type, capacity, `dev_t`, GPT, PARTUUID, mount source, filesystem or root/source overlap before any write. Synthetic sysfs and disposable loop fixtures exercise negative cases; no live identity is inferred from them. |
| `lhs-02` | Offline | Explicit stage, arm and activation operations retain the original recovery script, verify exact signed job/FIT/map, journal each durable boundary and publish the marker only after both environment copies read back armed. Disposable media fault cases show an interrupted stage retains normal boot or original recovery and never automatically enters the writer. |
| `lhs-03` | Offline | A dry-run/default refusal, artifact provenance, focused regressions and a reproducible operator handoff identify the exact remaining physical checks. No real block device is opened for writing during offline tests; the previously reviewed QEMU writer and normal A/B paths remain intact. |

One offline task implements all three checks so the safety boundaries are
reviewed together. The existing feature's `urh-04/05` and the single [H12
human task](../../hardware/coordinated-human-tasks.md) remain the physical
acceptance path. Passing `lhs-01/02/03` cannot mark them complete.

## Human dependencies

Restore printer Ethernet and report its power/USB-serial state. Arm
receive-only Beelink serial capture before any serial reconnection or boot.
Then record current CID, controller, `dev_t`, GPT, partition-five mount,
free space and original recovery-script hash using read-only inspection.
Only after that evidence and the exact artifact/recovery plan are reviewed
may H12 use the live stage/arm path. The factory eMMC stays stored; no module
move is needed. This is the same H12 session, not a second physical task.
