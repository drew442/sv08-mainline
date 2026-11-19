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


## Preserving legacy data during the first supported installation

A backup from an older installed release is not automatically compatible with a
new normal image. Recovery activation still requires the reviewed release, state
schema and release revision; normal boot still rejects unannounced releases.
Do not relabel an old registry, invent trial/health records, or select fresh state
while claiming that the old identity and application data were migrated.

For the initial schema-1 immutable installation, the coordinator can prepare a
**derived installation archive** with
`scripts/prepare_recovery_installation_archive.py`. This is offline preparation on
a development host in a private mount namespace, not a device writer or a recovery
permission override. It requires the original archive SHA256, the measured source
slot/release/schema/revision/generation, and the exact normal image, composition
receipt and their pinned hashes. Its `--source-revision` is the **target image's
project Git revision**, not the older installed release number. The normal A
manifest is read from the actual verified image partition; a supplied manifest
alone is insufficient. Run `--help` for the exact required flags.

The helper preserves the original archive, original generations and registry
backup, system/shared identity and application configuration/calibration. A new A
generation receives the target release and MCU recommendation. SQLite committed
WAL data is recovered into that new generation; old generation bytes remain
unchanged. Any active `system/klipper-start.json` is preserved in the preparation
backup but quarantined from its active location. A new explicit commissioning
permission is required; no MCU is flashed and no service is started. Writable or
customized OS state, unsupported schemas/links, unfinished operations, changed
inputs and insufficient space refuse without a successful output.

The derived archive is exported and restored into another disposable directory
and must pass unchanged activation compatibility and preservation checks before
its private `installation.tar` and receipt are published. Keep **both** original
and derived archives private. Successful preparation is not hardware, installation,
OS-health or printing acceptance. Independently assess the exact preparation and
backup evidence before relying on it for destructive installation; that later
operation also needs its existing exact-target review and owner authority.

Export and restore SD images retain distinct immutable media topologies. Use the
backup interface to create the real archive first; its random filename is known
only after execution. Bind the actual checked derived archive into the restore
profile. The [commissioning session](../hardware/test-sv08-01-commissioning-session.md)
records power-isolated media exchanges and the existing read-only NFS full-image
source. Neither an extra NFS mount nor mounted export/restore targets may be
carried into an operation whose strict admission excludes them.
