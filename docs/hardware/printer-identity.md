# Persistent printer identity

Cockpit's **Printer identity** menu manages the printer's certificate authority,
SSH access and identity backups. Administrator authorization is required.

Download **CA certificate** and import it as a trusted certificate authority on
clients that access the printer. Cockpit and Mainsail use certificates signed by
this CA. The CA stays on `/data/sv08/system/identity`; service certificate renewal
and OS replacement preserve it. The current host name, `.local` names, canonical FQDN, qualified names from
configured DNS search/domain suffixes, global IP addresses and loopback names
are covered. See [the SAN correction](printer-identity-san-20261008.md). A daily check renews the service
certificate with fewer than 30 days remaining or changed names. Certificates are
valid for one year; the CA is valid for twenty years. CA replacement is an
explicit identity restore, never an automatic response to damaged authority.

Under **SSH access**, upload public `.pub` files or paste one public key per line,
then review the complete trusted list and confirm. These keys authorize the
normal `sv08` account. Keep a key whose private key you possess. Private client
keys, authorized-key options and an empty trusted list are refused. Existing SSH
sessions stay open; subsequent connections use the selected list. The normal
host retains key-only SSH authentication. Existing persistent Ed25519 host keys
and authorized public keys are migrated when the CA is first provisioned.

**Download identity backup** produces a private, unencrypted ZIP containing the
CA certificate/private key, SSH host public/private key and trusted user public
keys. Store it privately. It excludes account passwords, client private keys,
hostname/network settings, machine ID, printer configuration and calibration.
After an OS replacement or persistent-storage replacement, upload the backup,
review its CA and SSH fingerprints and confirm **Restore printer identity**.
The restored authority signs fresh service certificates for the current printer
addresses. Restoring a different authority requires trusting that CA and accepting
its SSH host identity. Web services reload and the browser may need reconnecting.

The finite helper checks manifest hashes, complete key pairs and CA signatures
before selecting a generation. A stale revision or invalid/oversized bundle
leaves the current selection unchanged. Selection uses an atomic symlink;
complete active and previous generations are retained. Invalid/interrupted
entries are retained for inspection, with a hard eight-entry cap. Private keys
are root-only; the web-service key is readable by the service group. Mutations
participate in the shared data allocation lock and preserve configured free-space
and inode reserves. Corrupt authority fails closed and can be replaced only by
an explicitly reviewed valid backup; it is not silently regenerated.

Recovery-image builders provide the owner's convenience login **recovery /
recovery**. Normal host authentication is unchanged. The minimal SD recovery
host accepts this password as well as the existing owner public key. The generic
local recovery image adds the account without adding networking. This is a
source policy and an isolated PAM/SSH-tested credential; existing physical
recovery media are not rewritten by this delivery.

Installed acceptance and remaining release/physical boundaries are recorded in
[the delivery evidence](../features/persistent-printer-identity/evidence.md).
