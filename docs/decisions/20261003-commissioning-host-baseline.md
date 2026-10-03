# Temporary confirmation of the initial commissioning host

Date: 2026-10-03. Status: approved bounded design; installed acceptance pending.
Authority: owner-requested commissioning goal and independent
[proposal decision](../features/commissioning-host-readiness/record.json).

The installed diagnostic image has finite A boot attempts, while its normal
transactional health coordinator is masked and requires production composition.
An ordinary initial boot has no update trial to confirm. Cockpit also needs the
already accepted persistent certificate directory repair and fixed host context.

Use a separately enabled commissioning oneshot for only the reviewed immutable,
initial A-only diagnostic generation. Preserve production validators and all
printer/RAUC masks. After identity, state, mount, GPT, environment and stable host
health checks under existing locks, selected upstream libubootenv may replenish
only `BOOT_A_LEFT`. A3 is a no-op. Retain uncertain outcomes and refuse automatic
same-boot retries. The [proposal](../features/commissioning-host-readiness/proposal.md)
defines the full bounds and independent reviews.

Install an exact small overlay against measured installed source: accepted TLS
initialization, fixed admin context, supported Cockpit 337 Debian branding and the
explicit helper/unit/private binding. Preserve the old UI protocol. Shipping an
inert Python module through the existing general runtime inventory does not enable
the hook; default assembly must supply neither its unit nor private configuration.
The commissioning overlay remains deployable=false and does not establish printer
readiness, complete A/B qualification or a supported release.

Remove this hook, or let its strict applicability checks refuse it, when normal
production/update composition replaces the initial diagnostic baseline. A second
transaction coordinator, weaker production validation and broad runtime refresh
would expand the change beyond this temporary gap. No upstream fork is introduced;
the eligible-generation policy is project-specific, while the environment writer
and Cockpit branding mechanism remain upstream interfaces.

The owner's [password amendment](../features/commissioning-host-readiness/owner-access-amendment.md)
authorizes a simple initial password on this installed account. No password is
embedded in source or image defaults. It belongs to the current root overlay;
credential migration between images is outside this bounded boot/access check.

Sources: pinned U-Boot `boot/bootmeth_rauc.c` and RAUC
`src/bootloaders/uboot.c` revisions recorded in the proposal; project
`runtime/sv08_boot_health.py` and `runtime/sv08_rauc.py`; accepted TLS commit
`8c6f24f5a565cd08e43001414f643f55d5b1bb8b`; and
[Cockpit 337 branding](https://raw.githubusercontent.com/cockpit-project/cockpit/337/doc/branding.md),
accessed 2026-10-03. Physical evidence is recorded separately from offline tests.
