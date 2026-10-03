# H12 physical completion evidence — 2026-10-03

The reduced H12 outcome has been observed on test-sv08-01, board marking
H616_JC_6Z_V1.2 owner-reported. Independent record verification is pending.

## Session and write

The [session record](../../hardware/host-h12-attended-sd-session-20261003.md)
records exact runtime/source/target preparation, owner facts, independent delivery
and action review, and owner delegation of KVM confirmation. The reviewed
keyboard correction made native No/Yes selection explicit and passed installed
file-fixture and actual KVM journeys. On the independent SD root the production
backend checked the full 7,818,182,656-byte image, exact spare CID/controller,
capacity, source separation and target inactivity before confirmation. Actual
KVM showed matching image/target/destructive effect, default No, then visible Yes.

At 05:09:57 UTC coordinator confirmed through KVM under owner authorization.
By 05:23:26 UTC the screen reported matched full write/flush/readback. Target
written-sector count equals the complete image size. Source/target descriptors
were closed and target I/O was idle. The [write receipt](physical-write-evidence.json)
binds actual observations; this was not a file-fixture write.

## Installed normal boot

The first owner restart retained SD and therefore booted SD recovery. The owner
subsequently removed SD while powered and requested HW-667 control for resets.
SSH to that running SD system then closed. A fresh exact-operation review passed
for one five-second relay cycle; the earlier finite review was not reused.
Power cut at 06:30:50 and returned at 06:30:55 UTC. The printer USB bridge
vanished and re-enumerated, with no automatic repeat cycle.

Authenticated SSH returned as sv08 with a new boot ID. At 06:32:36 UTC, root was
read-only root-a PARTUUID 26c68198-9248-47af-bbd3-643f1b604ef5 on the accepted
32 GB MMC, whose CID matches the prior write target and controller is 4022000.mmc.
Only this MMC was present; no SD device was detected. Slot A was active, /data
mounted read-write, SSH active, and no systemd unit failed at observation. Actual
KVM showed the Debian 13 sv08 login. The [boot receipt](installed-boot-evidence.json)
binds the raw authenticated inspection and KVM screenshot by hash.

## Limits and subsequent operation

This establishes the accepted SD reimage, complete readback, operator-requested
restart and normal installed boot. The relay performed the physical power cycle
under the owner's request; it is not automatic maintenance return or boot policy.
SD remains available for recovery. Future resets use the tested HW-667; media
changes should be coordinated with relay power held off rather than asking the
owner to unplug USB. Do not repeat resets without need: the diagnostic image's
boot-health and RAUC remain masked and boot-attempt counters are finite.

No healthy release, printing, MCU, heater or motion is claimed. Historical
Cockpit/boot-health limitations are not declared repaired merely because no unit
failed at this observation. DPMS was disabled for the flashing session only.
Cold-start capture, RAM maintenance, permissions/forgery/replay/RNG/expiry and
separate rehearsal remain abandoned; automatic maintenance launch/return deferred.
