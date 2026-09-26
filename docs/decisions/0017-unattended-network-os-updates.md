# 0017: Unattended network delivery for A/B OS updates

Date: 2026-09-26. Status: owner-authorized feature scope; implementation and
hardware validation pending.

## Owner instruction

The owner requested a goal so routine eMMC updates need neither removal to a USB
writer nor human interaction for each flash. This supersedes the earlier plan to
defer Internet update delivery to a later release, for the bounded OS update
workflow below.

## Decision

Provide an opt-in/opt-out unattended release delivery path that obtains an
authenticated, signed SV08 OS release over the network, checks the configured
update policy and printer-idle admission, stages it through the existing RAUC
A/B transaction into the inactive OS slot, then arms it for the next normal
boot. Once automatic updates are configured, an individual OS update must not
require a person to upload, confirm, remove, or rewrite the eMMC. The running
slot and fallback remain intact during staging. Existing trial health and
fallback policy remains authoritative.

This is an in-place A/B OS update, not a raw whole-device eMMC image writer. It
does not rewrite the partition table, SPL/U-Boot, redundant environment,
independent recovery image, data partition, or MCU firmware. Those operations
remain separately scoped, reviewed and tested. It does not automatically
reboot a printer that is otherwise running; activation is on the next normal
boot.

The existing auto-update opt-out, customization refusal, immutable-root
requirement, verified-board compatibility, RAUC signature/payload checks,
printer-idle admission, transaction ordering, health confirmation and rollback
are mandatory. Network or feed failure must never mutate slots. No telemetry or
printer-unique identifiers are required for release discovery. A configured
feed must be authenticated, replay/downgrade bounded, size/time limited, and
bound to the installed hardware profile and release channel.

## Limits

This decision does not make the current non-deployable diagnostic image
eligible for writes. A physical A/B write and trial on a reviewed deployable
candidate, with the accepted recovery route available, remain prerequisites to
claiming the capability works on `test-sv08-01`.
