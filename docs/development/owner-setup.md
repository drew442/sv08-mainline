# Local owner password setup

Supported images explicitly declare `owner_setup: "recovery-v1"`. They contain a
locked `sv08` account (UID/GID 1000), a locked root account and an empty regular
SSH authorized-key seed. There is no shared normal-system password or project
owner key. Diagnostic images without this declaration retain their existing
provisioning behavior. The recovery convenience password policy is unchanged.

## Owner journey

In the independent recovery interface, choose **Set owner password**, the verified
storage target, and **Current state**, **Fresh state** or **Restored state**. Fresh
state must already have been explicitly created; restored state must already have
been restored. These choices map to the existing immutable recovery target policy,
not a typed path. Missing or damaged state is refused without initialization or
repair.

Choose **Initial password setup** for a state without an owner. To change an
existing password, choose **Reset existing owner password** explicitly. Local
recovery access is the security boundary for reset. Enter and confirm 12–256
printable ASCII characters; spaces are allowed. A physical keyboard or the built-in
touch keyboard can enter the password. Shift and Symbols expose uppercase and
punctuation; Next field switches between the masked entries. Review the account,
state and storage, then apply. Cancel leaves enrollment unchanged.

The password takes effect at the **next normal boot**. This operation does not
change currently running authentication, start services, activate state or select
an OS slot. Fresh or restored state still requires the corresponding explicit
activation operation. Sign in to normal Cockpit as `sv08`. Normal Cockpit Accounts
password changes and `passwd` for `sv08` are refused by a supported-image PAM
rule in both modes; use local recovery reset instead. Optional SSH public keys can
be enrolled through the existing Cockpit identity workflow after login.

Password setup does not commission the printer. After the separately reviewed
first Klipper start, persistent valid commissioning permission allows startup on
later healthy normal boots and compatible host updates in either root mode.
The supported boot helper checks that permission and all existing startup gates;
missing, revoked or stale permission leaves Klipper stopped and records a reason
in the `sv08-commissioned-start.service` journal. No Linux enable command or root
mode change is needed. See [service startup and acceptance](host-os-build.md#service-startup-and-acceptance).

## Persistence and boundaries

The root-owned mode-0600 `system/owner.json` stores only a salted SHA-512 crypt hash
and a random enrollment identifier with fixed account metadata. OpenSSL receives
the password over stdin through the existing `sv08_web.password_hash` helper.
Neither the password nor its hash is placed in a review, public status, log or
command argument. Passwords necessarily exist briefly in GTK/Python process memory;
this implementation does not promise secure memory erasure.

Review binds the selected target, state registry, root identity, current enrollment
and media fingerprint. Apply rechecks under the existing recovery media lease;
initial setup never replaces an existing record. Reset requires the reviewed
current record. Unknown formats, unsafe permissions, links, changed state/media,
interrupted activation and inadequate storage/inode reserves are refused.

At each supported normal boot, only the `sv08` password hash is merged into that
slot's own account files. Other accounts and all aging fields remain slot-local. Supported builders must provide a usable
non-expired `sv08` aging policy (an empty last-change field disables forced password
aging); last-change `0` would require an unsupported first-login password change.
In immutable mode, a private ephemeral file is bound read-only over `/etc/shadow`.
In writable mode, after the root remount, boot atomically updates the regular
slot-local shadow, preserving its UID, GID, mode and all aging fields. There is no
shadow bind in writable mode: package tools can append system users or atomically
replace shadow, and their account entries survive the next boot of that slot.

Supported image staging prepends the static
`configs/host-os/supported/owner-password-policy.conf` rule before the existing
`common-password` stack. It refuses password changes only for `sv08`; all vendor
rules and other users retain their normal password path. The finalizer rejects a
missing or reordered policy. Root expert direct shadow edits are unsupported
customizations, and boot restores the persistent owner hash on the next boot.
An absent enrollment keeps `sv08` locked; a malformed existing
record fails closed. Boot does not create or repair enrollment or missing state.

The persistent record is shared across A/B slots and operating modes. Complete
user-data export/restore preserves it with private metadata. Explicit state
activation selects the candidate's owner enrollment; retained state rollback
restores its previous enrollment. No whole `/etc` overlay or persistent copy of
slot system accounts is introduced.

## Source validation

Focused checks are `tests/test_owner.py`, `tests/test_recovery_owner.py`,
`tests/test_host_mounts.py`, the existing boot/admin/restore-media tests,
`tests/recovery_owner_gtk.py` under Xvfb at 800×480, and
`tests/host_mount_namespace.py` in a private disposable root mount namespace.
The latter requires root-owned safe scratch ancestry. These establish offline
behavior; assembled native Cockpit/PAM login and named-printer release acceptance
remain separate integration checks.
