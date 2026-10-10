# Owner request — 2026-10-10

Complete a short, bounded comparison of H616 Crypto Engine offload on the installed
stack. Use agents. Measure only crypto-engine/offload paths, not a separate CPU
software baseline or network/storage/update/reboot stages. Estimate automatic-update
availability-to-ready time assuming gigabit source access and no idle wait, using
specification-based assumptions for the remaining stages. Preserve actual timing
versus modeled timing and CPU crypto instructions versus the separate Crypto Engine.
No update installation, reboot, physical-media write or printer outputs are requested.

The owner accepts individual advanced update policy overrides instead of a blanket
bypass: trusted provenance remains required for automatic updates, explicit manual
provenance overrides are allowed, and version/compatibility/customization policy may
be individually configurable. Implementing those product controls is outside this
measurement goal; the earlier suggestion to remove signing does not govern it.
