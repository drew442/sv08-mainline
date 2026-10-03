# Owner amendment: initial Cockpit password

Date: 2026-10-03. Authority: explicit owner instruction during implementation.

The owner requested that the coordinator choose a simple initial password for the
existing `sv08` account, so no private terminal or manual password-setting step is
needed. The owner can change it later; do not require a change at first login.

This supersedes only the owner-set password and owner-performed login wording in
[the approved proposal](proposal.md). Actual authenticated browser login, elevation,
status, Stop, logout/relogin and persistence must still be observed. The coordinator
can perform these checks. SSH key access and existing PAM/sudo policy stay intact.
The password is supplied privately to the installed account and communicated to
the owner; it is excluded from repository files, command-line arguments and public
logs. This is an operational credential choice, not a new provisioning feature or
a universal password embedded in images.

The original approval and its hashes remain historical evidence. Software scope,
checks, independent verification and the exact-operation review before installation
remain unchanged. This amendment must accompany installed action and delivery
review packets. At the time of recording, the password has not yet been installed.
