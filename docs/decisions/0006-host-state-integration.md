# 0006: Persistent state and A/B integration boundaries

Date: 2026-09-09. Status: implementation candidate, offline tests only.

## Decision

Use upstream RAUC for signed paired boot/root installation and upstream U-Boot's
RAUC boot method for bounded slot selection. Add a small Python integration layer
for the gaps neither owns: persistent operating-mode policy, application-state
generations, customization records and package admission. This implements parts
of [decision 0004](0004-os-operating-modes.md); it does not supersede its acceptance
criteria. The printer remains offline and no board boot chain is validated.

`runtime/sv08_state.py` publishes its registry with an exclusive lock, fsync and
atomic replacement. Each slot refers to a separate application-state generation.
A staged update records its intended release, but copies config/database/UI state
only at the new slot's first boot, before application writers start. SQLite backup
includes committed WAL records. Unsupported schemas, links, concurrent state
changes and insufficient copy space stop preparation. Original state remains
available for rollback. G-code, timelapse, logs, owner home, network settings and
host identity are shared explicitly, rather than rolled back with application
settings. Orphan generation cleanup and migration beyond schema 1 remain open.

An initramfs-tools local-bottom hook fscks/mounts the explicit data partition
and binds persistent machine ID and hostname before systemd PID 1 starts. Debian's standard fsck hook is selected with `FSTYPE=ext4`. The transient machine-ID
commit service is masked because this identity is already persistent. Random
seed, time, rfkill and linger state have explicit mounts; systemd generates the
seed on the device. No cloned seed or SSH private key ships in a release.

The boot integrator verifies root/data block-device identities against explicit
image PARTUUIDs before mounting the matching boot partition. Immutable/writable
mode changes apply at boot. There is no shared root, `/etc`, `/var`, or package
metadata overlay. Entering writable mode permanently marks that slot customized;
returning to immutable preserves those files and the customization record. Image
trials are blocked for customized systems pending explicit reconciliation.

The current package wrapper requires writable mode and stopped managed printer
services. It never stops a print itself. It holds a shared admission lock and
records the operation and resulting package inventory privately; an APT preinvoke
hook checks its lease. Service start checks use that same lock. This is an initial
stopped-service workflow, not yet the required live idle-staging mechanism. Root
owners retain control and can bypass this policy. Kernel/boot package hooks are
not validated for writable mode and must not be offered as supported updates yet.

Trial boots create a marker that prevents Klipper service startup. Health checks,
RAUC mark-good coordination and release of this gate are deliberately outstanding;
there is no automatic success declaration based merely on systemd starting. Image
staging, boot selection, health confirmation and MCU updates remain separate.

## Evidence and retirement

The implementation is original project integration, using Python standard-library
filesystem/SQLite APIs and systemd mount/service configuration. Regression tests
cover late writes, WAL, rollback, interrupted copy, mode preservation, corrupt
state, ownership repair, device identity and package admission. A real Linux mount
namespace test checks read-only enforcement and persistent writes. A target ARM64
systemd unit verification checks ordering; none is a full Linux boot or a printer
test. [Build evidence](../hardware/host-state-build.md) records scope and sources.

Retire custom components individually if upstream RAUC/state-migration integration
provides these semantics, or upstream printer service APIs provide atomic idle
admission. Keep project-specific state policy outside upstream checkouts. Any
upstream proposal must include the failure tests, without private printer state.


The subsequent [transaction implementation](../hardware/host-transactions.md)
orders durable installation, pending trial, boot selection, confirmation and
cancellation. Its production backend/admission/health callbacks are still open;
it does not enable automatic updates or declare a printer healthy. The
[signed bundle policy](../hardware/host-bundle-policy.md) supplies the separate
layout/state/Klipper admission check.
