# Verified pre-mounted media for recovery export

Kind: feature. Author: pilot_suggester. Date: 2026-09-12.

## Problem and evidence

The installed recovery entry point constructs a controller without an operation
adapter. The archive exporter and GTK/FAT fixtures work offline, but their admission
callbacks rely on facts supplied by the test caller. A user cannot yet reach a
verified media/export workflow from the configured recovery UI. See
[existing export evidence](../../hardware/host-recovery-export.md),
`runtime/sv08_recovery_ui.py`, `runtime/sv08_recovery.py`, `runtime/sv08_export.py`
and `tests/recovery_export_mounts.py` at baseline `2444ede`.

This is unfinished work already required by
[decision 0010](../../decisions/0010-host-administration-and-recovery-ui.md).
The suggestion role inspected it independently of the framework implementer.
No printer, physical USB medium or private backup was accessed.

## Intended outcome and scope

Connect the actual GTK selection, review and apply workflow to an explicit trusted
configuration of already mounted recovery/data/removable media. Verify the running
recovery context, actual mount/block ancestry and source/destination separation;
hold exclusive admission and recheck identities before export. Without a verified
context the installed UI stays diagnostic-only with an understandable reason.

Prove the complete workflow with real disposable filesystem mounts and a source
registry that is damaged but still exportable. Keep source files and pre-existing
destination files unchanged. Preserve all existing exporter checks and staged
runtime-source consistency checks.

This slice does not mount arbitrary devices, guess a board/MMC identity, format,
restore an OS, select a boot slot or assemble the independent recovery image.
Production context must be distinct from fixture-only identities. Any mount
property that cannot be established is a refusal, not an inferred permission.

## Alternatives and cost

Existing export and native controls provide the archive/UI behavior. Add only the
missing media/context admission provider, its entry-point wiring and tests. Reuse
kernel mount/block information and existing operation contracts. An upstream
recovery provider can replace this adapter when it supplies equivalent identity,
quiescence, exclusion and preservation guarantees.

Browser image upload remains valuable but currently needs authenticated intake,
owner/login integration and durable jobs. The recovery path has more existing
end-to-end fixture coverage and supplies the smaller first offline pilot.

## Acceptance

- `admission`: refuse unknown/wrong running context, writable source or alias,
  same-system-medium destination, disappeared/replaced medium and competing lease.
- `gtk-fat`: run the actual GTK/controller/export path through the provider using
  read-only source and disposable FAT media; preserve damaged source and existing
  destination data. Review cancellation creates no archive.
- `staging`: package the provider and preserve mismatched-runtime rejection and
  diagnostic-only behavior when context is absent or invalid.
- `physical`: separately validate the configured independent recovery system,
  actual USB discovery/removal, physical inputs and attended failure behavior on
  an identified profile. Offline fixtures do not satisfy this check.

The offline task owns the first three checks. The physical task remains blocked
and does not block independent offline improvements after integration.

## Human dependency

Use [the existing human checklist](../../hardware/host-os-tasks.md#human-and-powered-printer-tasks)
for a reviewed bootable recovery candidate, actual media/input testing and attended
failure tests. Test printer 01's host PCB revision remains unknown for this work.
The printer is deliberately offline; this proposal grants no permission to access it.
