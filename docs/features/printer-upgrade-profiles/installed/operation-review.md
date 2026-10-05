# Exact software installation assessment — 2026-10-05

The owner requested installation of the published simplified hardware page and
named upgrade profiles. An independent `high_consequence_reviewer` assessed the
exact overlay before execution and returned **PASS WITH CONDITIONS**. Its role
configuration declares GPT-6.1 Sol/medium; effective runtime model and effort were
not independently observable, so no runtime verification is claimed.

Reviewed source: `cca84ba5e69c4de6ec7af1dc4dfae6ea8a19256c`.

- Operation SHA256: `d2ee103bed859905cb9e174ec6fe9905660cd87cf39c9b78a344d26dc1284c77`.
- Packet SHA256: `65833e5a90a192dc10967925a743c414a554115bc1ff89cb9451b428c4b34425`.
- Hash-bound wrapper SHA256: `6333461881272a2bff68e897e55fc0c35ad51dc25de008ef2faddc2540222958`.

Eleven changed files total 296137 payload bytes. Ten match the named source
commit byte for byte; the compiled host HTML preserves its recorded preimage
outside the embedded printer panel. The operation adds two source directories,
checks exact boot/CID/root target, public file preimages and directory inventory,
saved context hashes, masked inactive services, absent live configuration and
capacity. It saves durable private originals before root remount, replaces files
atomically with host HTML last, and restores original files/removes added files
and directories on admitted failure. This is per-file atomicity, not whole-set
power-loss atomicity. Boot, services, live configuration and recovery are outside
the write set.

The conditions require exclusive publication without browser RPC/configuration
writes; PSU OFF; retained private rollback/packet/status; reconciliation after any
interruption instead of blind retry; immediate exact file/directory/context/boot/
CID/read-only mount/service/capacity checks; the same preservation checks after
an authenticated browser journey with no Save/apply; and no hardware compatibility
or printing claim. The hash-bound wrapper repeats target admission before writes.
The reviewer found the concrete risks to be a wrong target, concurrent mutation
or writable root after failure; the guards and recovery address these within the
stated conditions. It performed no remote access or changes.
