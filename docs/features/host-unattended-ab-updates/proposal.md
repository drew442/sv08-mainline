# Host unattended A/B update delivery

Kind: feature. Author: root-coordinator. Date: 2026-09-26.
Requirements: [decision 0004](../../decisions/0004-os-operating-modes.md) and
[owner-authorized decision 0017](../../decisions/0017-unattended-network-os-updates.md).

## Problem and evidence

The project already has a signed RAUC A/B backend, authenticated browser upload,
durable image jobs, an automatic-update opt-out, and transaction/boot-health
handling. `ui/host/index.html` lets an owner upload a `.raucb` and separately
review staging and arming. The existing transaction API supports
`automatic=True` (`runtime/sv08_transaction.py`), but
`runtime/sv08_admin_images.py` does not use it for background work and
`runtime/sv08_admission.py` explicitly says it is not an enabled scheduler.
`docs/hardware/host-rauc-backend.md` says automatic idle/next-boot policy and
production wiring remain open. The current update flow therefore needs a person
to supply and submit each release.

Separately, H10 proved that a diagnostic Linux boot could open the installed
spare eMMC read-only and inspect its U-Boot environment. It did not exercise any
write. The current board manifest remains non-deployable and the independent
recovery image is diagnostic. Neither may be treated as authorization to write
the physical printer.

## Intended outcome

When a user enables automatic updates and the printer is idle, a fixed host
service checks the configured signed release feed, downloads a compatible
release, reuses the existing RAUC transaction to write only the inactive OS
slot, and arms it for the next normal boot. The user may opt out at any time;
opt-out prevents future checks/staging but does not silently discard an already
armed release. An individual routine OS update needs no writer, SSH command,
per-release upload or confirmation.

This is an in-place A/B OS update. It does not raw-flash the whole eMMC or
replace SPL/U-Boot, the redundant environment, independent recovery, `/data`, or
MCU firmware. The updater must not reboot while a print may be active. Existing
health confirmation and rollback remain the only way a trial becomes good.

## Scope and alternatives

Use one fixed update source configuration, authenticated transport, a signed,
bounded channel index and the already installed RAUC release keyring. Require
fresh channel metadata, a monotonic release sequence, exact hardware/profile
compatibility, a bounded bundle size, and a separately valid signed RAUC bundle.
Reject redirects outside the configured HTTPS origin. The source carries no
printer serial or usage telemetry. Do not make URLs, executables, device paths,
keyring paths or systemd properties browser-controlled.

The feed check and staging operation must obey the persisted automatic-update
setting, current boot/release identity, immutable mode, customization policy,
transaction revision, storage bounds, RAUC writer exclusion and atomic printer
idle admission. Failure before backend mutation leaves both slots and boot
selection unchanged. An uncertain write is reconciled from the transaction
journal; do not retry just because a timer fires. Staging/arming must be
idempotent across repeated feed checks and process restart.

Expose last check/result, available release, and a plain reason when the update
is blocked in the existing host UI. Do not auto-reboot: successful staging and
arming take effect on the next normal boot. Retain the current upload-and-review
path when automatic updates are disabled or unavailable.

No new server account, telemetry, package manager, raw-disk writer, generic job
framework, automatic MCU updater or product UI redesign. Keep the feed protocol
small and retire custom code if an upstream RAUC-supported mechanism provides
equivalent signed discovery, anti-replay, admission and A/B semantics. The
release-signing key remains offline; the test feed uses disposable signing
material only.

## Acceptance and task split

The source/index schema and signature must bind a release channel, monotonic
sequence, expiry, hardware compatibility, bundle size and digest. A signed
index alone does not replace RAUC bundle signature and payload verification.
Offline tests must use real cryptographic signatures, a local deterministic
server, the production updater/transaction code, and a disposable QEMU disk.
Test opt-out, busy printing, custom/writable mode, stale and replayed metadata,
redirects, truncation, disk exhaustion, current-state races, repeated polls and
process/power loss around the RAUC write. Confirm that A stays running during
staging, only B's pair changes, and automatic activation still waits for a
normal reboot and real health confirmation. Run rollback and prove no
partition-table/environment/recovery/data/MCU write.

Before enabling the service on a printer, independently review the complete
candidate, its deployable board manifest, signature keyring, target backend,
recovery route and write bounds. The later physical test uses a named profile
and a disposable signed release, one attended serial capture, a safe idle
printer, and no eMMC removal. It records the inactive-slot write, next boot,
health result and fallback readiness separately. It does not claim release
qualification or printing readiness.

## Human dependencies

The offline implementation can proceed now. Physical commissioning is queued as
[H11](../../hardware/coordinated-human-tasks.md) and remains blocked until a
deployable candidate and independent high-consequence review exist. The owner
need not remove the eMMC or connect the USB writer for the eventual A/B trial.
This limitation concerns the one-time validation session; once the signed feed
and policy are commissioned, routine updates require no per-update human action.
