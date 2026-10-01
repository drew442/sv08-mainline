# Coordinator artifact storage — 2026-10-01

The coordinator root had only 3.5 MiB free, preventing sustainable required
implementation/review work. Beelink had 31 GiB free after its previously authorized
VG expansion. No coordinator LV expansion was performed.

The historical ignored QEMU artifact
`build/host-qemu-rauc-resolution-113-v1/root.ext4` was archived to Beelink at
`/srv/sv08-artifact-archive/20261001-rauc-resolution-113-v1-attempt02/root.ext4.gz`.
Original logical size is 2,147,483,648 bytes, allocated size 1,400,250,368 bytes;
SHA-256 is `e1adb8a447cc841d4dce674a0c85a39f732bd13fb134a3008b44a2a21b1f5418`.
The private gzip is 583,206,741 bytes. Remote decompression matched the original
size/hash before durable publication; a separate full readback reproduced them.
Both archive and receipt were fsynced before local retirement. Source identity,
mtime and hash remained unchanged; no process fd or loop device used it, and it
had no xattrs. The candidate's other files and all Git history remain unchanged.

The local duplicate was then removed, releasing approximately 1.3 GiB. Its private
`root.ext4.archive.json` receipt remains beside the other candidate files, recording
archive location, original owner/mode/mtime and sparse restore instructions.
Full before/readback/retirement receipts are in ignored
`local/feature-workflow/probes/artifact-archive-20261001/`.
Restore this regular file and verify its hash before reusing that historical VM
candidate; its original pathname no longer contains a locally readable disk.
The first unprivileged source-read attempt was denied by the root-owned fixture
parent and retired nothing; the corrected coordinator read streamed directly into
compression. This is evidence preservation and resource recovery, not a new VM
validation, image modification or hardware operation.
