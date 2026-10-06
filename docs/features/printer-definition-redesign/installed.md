# Installed printer hardware redesign — 2026-10-06

Owner request: “install it”. Installed source `4586c1e` on test-sv08-01,
the existing spare-eMMC A root. [Sanitized receipt](installed.json) binds all
22 installed file hashes/modes and the exact reviewed installation packets.

Independent high-consequence assessment passed before each root-filesystem write.
The main overlay is 495,517 bytes, including the exact simulated-MCU validation
dictionary; the second 5,880-byte CSS overlay corrects inherited host-navigation
button widths that squeezed the Advanced label at 1024 pixels. Source code is
unchanged apart from that scoped layout correction.

Both installations used a unique bounded systemd one-shot, exact fresh target,
boot/context/inventory/preimage checks, PSU-OFF admission, private original-byte
backups, atomic file writes, readback and rootRO restoration. Final observation
confirms the same CID/root/boot, root and boot read-only, data writable, seven
printer services masked/inactive, unchanged saved state and unrelated assets,
PSU OFF and no active printer.cfg. Installation units are inactive with MainPID0.
Retain both rollback backups on /data; a future rollback must first admit current
bytes and restore the exact reviewed originals.

Authenticated installed Chromium acceptance passed with the actual ARM64 helper:
seven cards, factory bed choices, Advanced collapsed, source manager, connections,
single host shell, reload, unchanged saved state and no page-wide overflow at
1440×900, 1024×600 and 390×844. The corrected Advanced label remains one line.
The first browser attempt had an overly specific test predicate expecting “SV08”
in the factory bed label; matching the actual committed factory label corrected
the invocation without production changes. A subsequent successful screenshot
exposed the inherited CSS problem, which was repaired and retested on the printer.
Raw browser profiles/screenshots, authentication data and private originals are
excluded from this record. The temporary SSH test tunnel was closed.

This is installed UI/runtime evidence. No live configuration application, service
restart, MCU connection, heating, movement or printing release was performed.
Third-party definitions remain deferred; only factory SV08 choices are bundled.
