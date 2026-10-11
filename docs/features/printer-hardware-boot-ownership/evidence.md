# Hardware loading ownership repair

The physical status helper refused with `Feature directory must be private and owned`.
Saved hardware storage and both files were 1000:1000, with correct 0700/0600 modes.
Boot preparation recursively chowned all config descendants to the application user.
PrinterStore correctly requires root ownership of this private managed subtree.

Restored only ownership of active config/printer-hardware, state.json and .lock,
with exact type/mode/owner guards and nonblocking feature lock. SHA256 of state.json
remained `3141fd19d4b4ad03af96c23fe2d3bd78efd01335191225baf9c6556a94078a39`.
Physical helper subsequently returned revision13,24devices,26definitions,1source,
current and previous candidates present. No stored contents or protections changed.

Boot preparation now assigns this exact subtree to root; ordinary application state
still belongs to the application user. Ten boot tests passed, including current and
copied-generation ownership assignment, unchanged bytes/modes and fallback untouched.
Ownership calls are mocked in that regression; actual physical ownership recovery
and helper success are separate measured evidence.

The coordinator inspected the complete stable diff and installed the changed boot
module only after exact preimage/hash/type checks. Original module retained beside
UI rollback archive. Root restored read-only; no module execution, reboot, printer
activation, configuration application or inactive-slot modification. No authenticated
physical-browser rendering proof claimed. [Exact results and hashes](evidence.json).

Commands/receipts retained privately under
`/home/drew/.sv08-cockpit-deploy-20261011/`; configuration response contents are excluded
from publication. Self-validation under proportionate development review.
