# Automatic update policy and activation

The [owner request](../features/automatic-update-policy/owner-request.md) extends
[ADR 0017](../decisions/0017-unattended-network-os-updates.md): automatic updates now
request a controlled idle reboot, and customization refusal is an individual
policy check. Other storage, recovery, admission and health protections remain.

Cockpit **OS images & updates** enables/disables automatic updates. Its advanced
section configures independent checks. Manual upload/staging has separate
advanced choices; every review binds those choices to state revision and, for
staging, the exact uploaded SHA-256. Upload does not install or activate anything.
No global keyring changes, service restarts or persistent manual trust bypass occur.

| Option | Default | Scope |
| --- | --- | --- |
| `check_compatibility` | true | Compare the bundle's declared compatibility label; physical target/layout checks still apply. |
| `check_customization` | true | Refuse replacing locally customized OS slots. Turning it off permits a fresh OS, preserving the running source and persistent user settings, without copying installed OS software. |
| `check_version` | true | Require explicit known release revisions and refuse the current revision. |
| `allow_downgrade` | false | Permit an older revision when version checking is enabled. |
| `allow_untrusted_provenance` | false | One reviewed manual operation only; never valid for automatic policy. |

Automatic metadata and bundles always require trusted signatures. The index's
publication sequence is an anti-replay counter, independent of release ordering.
A newer publication sequence cannot bypass the downgrade check. The fixed HTTPS
origin, trusted-time/expiry checks, metadata signature and sequence persistence
remain enforced even when the configurable checks are disabled.

Release publishers add a positive decimal `release-revision` under `[meta.sv08]`
in the RAUC manifest, alongside the existing exact `layout`, `state-schema` and
`klipper-commit`. Mirror it as an integer `release_revision` in the signed feed
index and the installed `/usr/lib/sv08/release.json`. Boot records this explicit
image revision in the slot registry; identifiers such as `release-2` have no
inferred ordering. Older images without it require an explicit version-check
exception. Reusing a registered release identifier remains prohibited because
state generations must stay unambiguous. Layout/state-schema/Klipper pin, exactly
paired raw images/dimensions, no hooks, device identity, inactive-slot selection,
immutable running root, capacity/state-copy reserves, source preservation and
installed-image readback cannot be disabled through these options.

The [pinned RAUC patch](../../patches/rauc/README.md) adds
`--ignore-signer-trust` for inspection and installation and its per-request D-Bus
option. It skips certificate-chain trust only, retaining mathematical CMS
signature verification and full verity payload checking. Inspection proof records
`signer_trusted=false`; installation rechecks the same proof and binds the external
manifest hash. Unknown/expired signers can therefore be accepted manually, while
damaged signatures, corrupted payloads and missing/malformed CMS are refused.
Literally signature-free files are not supported RAUC verity containers.

`state.json` retains optional strict `update_policy` booleans for automatic
admission. Transactions record origin, effective policy, its revision, signed
release revision and the complete admission proof. Stage/arm/reboot recheck current
policy. Once a trial boots, health/fallback use its admitted policy, so tightening
future policy cannot strand a correctly admitted customized source or clear its
customization record.

The fixed feed stages and arms through the existing transaction coordinator,
then uses shared network/restart idle admission. State and network locks exclude
policy edits, queued/uncertain software/image work and pending network rollback
through dispatch. `/run/sv08/shutdown.json` closes service-start admission.
`automatic-reboot.json` binds the request to transaction, source boot, release,
slot and policy; states distinguish ready, dispatching, queued, uncertain,
suppressed and observed. Acknowledgment means **queued**, never healthy completion.
Timeout, nonzero acknowledgment, interrupted caller or lost receipt after dispatch
retain admission closed and are never automatically replayed. Only proven failure
to launch clears the exact barrier and permits retry. Opt-out before dispatch
suppresses reboot but retains an armed trial. After dispatch may have reached
systemd, opt-out cannot promise cancellation. A changed boot waits for existing
health reconciliation; it cannot resend the old reboot request.

The timer remains ten minutes after boot and six hours after a completed check;
a busy printer may defer activation until another poll. Existing trial health
confirms or falls back. Validation uses real RAUC, systemd and synthetic ARM media,
with simulated printer/transport and host-modeled boot selection; it does not
qualify SPL/U-Boot, physical printing or an unvalidated flashable release. Physical
installation remains the existing coordinated hardware task.
