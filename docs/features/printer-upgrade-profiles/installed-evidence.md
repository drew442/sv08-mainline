# Installed simplified hardware page — 2026-10-05

The owner explicitly requested installation after publication of `cca84ba`.
Coordinator installed that exact source on **test-sv08-01**, preserved spare eMMC
diagnostic slot A. This is installed software acceptance, not heater/motion
commissioning or original-SV08 chamber compatibility.

The [independent exact-operation assessment](installed/operation-review.md) passed
with conditions. A hash-bound dry run and current target admission passed before
execution. Eleven files, 296137 payload bytes, update the simplified UI, embedded
host panel, matching printer catalog/generator/store and pinned module reference.
Two source directories were added. [Manifest](installed/manifest.json) records
exact afterimages. Host HTML bytes outside the panel and all unrelated installed
files are preserved. Private originals/packet/status remain under
`/data/sv08/printer-upgrade-backup-20261005`; per-file replacement and admitted
rollback do not claim whole-set atomicity across power loss.

[Immediate](installed/immediate-preservation.json) and
[final](installed/final-preservation.json) checks passed for all 52 installed
files and eight directories: hashes, modes, ownership, exact membership, saved
configuration/context, boot and CID identity, seven masked inactive services,
absent live printer.cfg and read-only root/boot. Data remains writable; final
capacity retains 512 MiB root and 768 MiB data floors plus inode reserves. PSU
was measured OFF before execution and after browser acceptance. No service,
boot, MCU, heater or motion operation occurred.

[Actual authenticated browser results](installed/browser.json) passed on the
installed ARM64 helper: collapsed advanced settings, named bed and chamber choices,
real component RPC selection, module add/remove, unsaved draft discard on reload,
single shell, preserved host/printer edits across navigation and Back/Forward,
legacy bookmark redirect, and desktop 1440×900, touchscreen-sized 1024×600 and
narrow 390×844 layouts without page-width overflow. The coordinator visually
inspected the desktop capture. No Save/apply request was issued; the legacy saved
two-sensor draft remains exactly unchanged. The existing legacy bed sensor was
removed only from the unsaved browser draft before kit selection to avoid its
intentional occupied-pin collision. Test choices were discarded; final logout
completed, own Chrome/profile and newly created SSH tunnel were stopped.

The first browser launcher stopped before browser/authentication because its
historical WebSocket shim required an unavailable undici module. Node 22's native
WebSocket corrected the invocation; no dependency was installed. The old tunnel
PID no longer existed, so a new owned tunnel was admitted against the same target
and pinned TLS certificate. No installation was replayed. Private receipts and
screenshots remain in `local/feature-workflow/probes/printer-upgrade-install-20261005/`;
[artifact hashes](installed/artifacts.json) retain the evidence binding.

Funssor's supplied thermistor specification and original-SV08 CAN adaptation/module
firmware compatibility remain pending. Hardware choices can be saved incomplete;
the installed page does not invent missing sensor or connection identities.
Older feature records/evidence retain their historical scope and pending physical
requirements; this owner-requested installation provides the current software
receipt without waiving those requirements.

The [2026-10-06 legacy sensor repair](legacy-sensor-repair/evidence.md) fixes
assembly selection against the preserved older sensor names and records the
current two-file installed follow-up.
