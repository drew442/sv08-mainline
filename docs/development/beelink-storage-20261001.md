# Beelink root storage expansion

2026-10-01. Actual development-host operation completed; this is separate from
printer hardware, image compatibility and release qualification.

The owner authorized expanding Beelink's
`/dev/mapper/ubuntu--vg-ubuntu--lv` using free VG extents if needed. Root had
about 1.5 GiB available at 99% use. Upcoming factory-capacity compositions need
space while retaining existing candidates. A bounded 32 GiB addition leaves
most unused VG capacity available for later allocation.

| Observed item | Before | After |
| --- | --- | --- |
| Root LV | 100 GiB | 132 GiB |
| Ext4 block count, 4096-byte blocks | 26214400 | 34603008 |
| Root available space | About 1.5 GiB | About 31.7 GiB |
| VG free space | About 111.4 GiB | About 79.4 GiB |
| Separate QEMU LV | 24 GiB | Identity and size unchanged |
| Root filesystem error counter | 0 | 0 |

A separate `high_consequence_reviewer`, with GPT-6.1 Sol/medium runtime
observed, reviewed the exact host/volume/filesystem plan and independently
measured its identities, geometry and capabilities. Test-mode LVM output was
retained as simulation evidence. A private VG metadata backup was fsynced and
copied to the coordinator with exact SHA-256 readback before growth. This
metadata backup is not a filesystem or user-data backup.

Fresh host, boot, root mapping, LV/VG/PV/filesystem identities, geometry, free
extents, other-volume size, executable hashes and zero-error checks preceded
one exclusively recorded `lvextend --yes --extents +8192` invocation. It
returned zero and grew only the identified root LV.

The intermediate parser expected two LV report rows; LVM returned three segment
rows for two volumes after the allocation. It stopped before filesystem growth.
The original refusal and validator remain evidence. A corrected validator
accepts duplicate rows only when their complete LV metadata agrees, requires
exactly the two expected volume identities, and preserves all physical gates.
Actual before/intermediate states passed and corrupt states were refused. The
same separate reviewer issued a new exact review for the remaining filesystem
step after independent segment/geometry measurements.

Following fresh admission and a separate exclusive intent, one `resize2fs`
invocation returned zero and grew the mounted ext4 filesystem online. Final
read-only checks confirmed its UUID and root mapping, writable state, exact
block count, 20332 remaining free VG extents, unchanged other-volume identity
and size, 33985306624 bytes available, zero filesystem errors and no target
ext4/block-I/O error in the bounded operation-window kernel observation.
No shrink, metadata restore, reboot or printer operation occurred.

Private metadata, UUIDs, source/tool/review hashes, one-shot intents, raw
receipts, preserved parser refusal and final result remain in ignored probe
storage. The recorded plan hash is
`88b0cc1ced368ecd210869a5b606db8aba31100afab603b7e8d844305e8f0849`;
the remaining-step plan hash is
`3d8e464a4f5b82044ded06e68bf7c9ef4a4475df50117ccc336b3bdc37345420`.
The actual result receipt SHA-256 is `5bc77726fe0d1449af1e1c5c414caeda403383223e5aaf63b258b2a4e55724a5`.

This enables development storage allocation. H12's physical preflight/reimage
and the [full project requirements](../remaining-work-plan.md) remain pending.
