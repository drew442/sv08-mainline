# Cockpit TLS persistence correction evidence

Date: 2026-09-25. Scope is bound by the approved small-fix record
[`task.md`](../features/host-admin-cockpit-tls-persistence/task.md). This is
offline evidence only; it does not certify production TLS or printer hardware.

The selected Cockpit package booted in ARM64 QEMU with the guest root mounted
read-only (`ro,relatime`) and a separate persistent data image mounted
read-write (`rw,nosuid,nodev,relatime`). The actual Cockpit HTTPS endpoint
returned status 200. Cockpit generated `0-self-signed.cert` (1,350 bytes) and
`0-self-signed.key` (1,704 bytes) under
`/data/sv08/system/cockpit/ws-certs.d`. The directory was mode 0700 and owned by
root:root. The private key hash is intentionally omitted from this tracked
record. The test stopped QEMU and confirmed workstation identity files and
Cockpit unit state were unchanged.

`tests/test_stage_admin_ui.py` covers missing/empty directory staging, the exact
persistent link, refresh, and refusal of populated/unexpected links without
overwriting them. `tests/test_host_boot.py` verifies the directory's owner/mode,
symlink rejection, and preservation of fixture certificate/key bytes across
repeat initialization and A-to-B generation preparation. `tests/cockpit_fixture.py`
adds the read-only-root, separate-data-disk TLS smoke path to the existing actual
Cockpit fixture. The private run record is ignored at
`local/cockpit-tls-persistence-20260925/tls-smoke.json`.

The proof does not cover a physical board boot, production LAN identity, a
factory-capacity fit, or authenticated browser administration on this candidate.
Physical TLS acceptance remains open in the host checklist.
