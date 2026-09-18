# Host boot and health composition intake

Planning baseline: 2026-09-18. This is a bounded implementation intake for
the existing host update transaction. It does not approve a new product
feature, authorize a printer write, or promote offline evidence to hardware or
release evidence.

## Finding and safe smallest slice

The durable A/B state machine already exists. `Transaction.reconcile(boot)`
classifies `idle`, `staged`, `needs-arm`, `awaiting-reboot`, `needs-health`,
and `needs-cancel`; `Transaction.confirm(boot, health)` requires a caller
supplied health result before marking a target good. RAUC validates the running
slot, immutable root, paired devices, environment, and slot status. These
behaviors are covered by [`runtime/sv08_transaction.py`](../../runtime/sv08_transaction.py),
[`runtime/sv08_rauc.py`](../../runtime/sv08_rauc.py), and
[`tests/test_transaction.py`](../../tests/test_transaction.py).

The missing production binding is at boot. [`runtime/sv08_boot.py`](../../runtime/sv08_boot.py)
prepares the persistent generation and boot record, then only creates
`/run/sv08/trial` for a trial boot. No production coordinator calls
`reconcile`, supplies OS health to `confirm`, or records a failed trial. The
existing Klipper unit deliberately keeps `ConditionPathExists=!/run/sv08/trial`
([`configs/host-os/systemd/sv08-klipper.service`](../../configs/host-os/systemd/sv08-klipper.service)),
and the Moonraker unit is similarly dependent on the prepare service. Only
Klipper is currently trial-gated. A host-only Moonraker `provider: none` may
run for diagnostics, but it must not cause printer startup macros or output.
The Klipper gate must remain through durable OS confirmation.

There is a second, material boundary: `Transaction.reconcile` and `confirm`
currently enter `Admission`, whose callback quiesces and stops Klipper and then
Moonraker. Therefore a health callback that requires either service active is
impossible, and `After=` ordering cannot establish application readiness. ADR
0009 explicitly reserves a separate confirmation policy; the existing
service-stopping admission is for staging/package work
([`docs/decisions/0009-atomic-idle-admission.md`](../decisions/0009-atomic-idle-admission.md)).

The smallest safe slice is consequently:

1. Add a boot coordinator at a proposed fixed path
   `runtime/sv08_boot_health.py` and an installed unit
   `configs/host-os/systemd/sv08-boot-health.service`. The unit runs after
   `sv08-prepare.service` while the Klipper trial condition still suppresses
   Klipper. It has a bounded timeout and writes durable bounded diagnostics;
   it has no unconditional `FailureAction=reboot-force`.
2. Give the coordinator an explicit boot admission separate from staging
   `Admission`: a root-only context manager that owns only a distinct boot
   confirmation exclusion and never reacquires `Store.locked()` or the RAUC
   writer. It must not call the Klipper quiesce socket or stop either printer
   service. `Transaction.reconcile` and `Transaction.confirm` already own the
   state lock and writer, so the injected admission is entered inside those
   existing state-lock scope, before the writer scope, and may only serialize boot coordination. The
   selected proposed API (coordinator decision, 2026-09-18) is:

   ```text
   Transaction.reconcile(boot, *, admission=boot_admission)
       -> classification
   Transaction.confirm(boot, os_health, *, admission=boot_admission)
       -> completed transaction
   ```

   The implementation may preserve the current default staging admission for
   callers, but the boot coordinator must pass the non-stopping boot admission
   to both target `reconcile` and `confirm`. The coordinator must never pass a
   callback stub as production health. Transaction retains the ordering state lock → selected admission → backend
   writer. The real `os_health` callback runs exactly once inside `confirm`,
   after identity checks and before mark-good; no precomputed `True` is passed.
   Health reads must not reacquire these locks. The bounded health window can
   hold the writer exclusion; its deadline limits that delay. Formal proposal
   review remains required before coding.
3. Define `HostHealth(boot) -> True` as OS health only. It must work on a fresh
   image with no `printer.cfg` and no connected MCUs. It checks the boot
   identity, selected slot, installed release/schema, persistent mounts,
   required host/update/recovery services, and the reviewed board environment
   and interface prerequisites. The proposed minimal checks are
   `sv08-prepare.service` active, `/data` mounted to the reviewed data device,
   the current boot record/generation readable, the immutable-root and paired
   device checks already performed by the read-only RAUC context validator,
   and the RAUC service identity/status check already exposed by
   `Backend.resolution_evidence`. If a host-only Moonraker provider is present,
   it may be checked as a local application; printer readiness, Klipper state,
   MCU reachability, sensors, heaters, motion, Wi-Fi association, and a display
   must not be confirmation prerequisites. An absent access point, DHCP lease,
   or MCU must leave diagnostics available and must not create a reboot loop.
4. Require a bounded stable interval in which those OS checks remain true.
   `After=` dependencies only order startup; they are not readiness evidence.
   Proposed acceptance values are a 5-second stable interval and a 60-second
   coordinator deadline. The proposed diagnostic bound is 64 KiB per boot
   record and 1 MiB retained per failed generation, with retention until the
   next reviewed cleanup or recovery export; these values need implementation
   review and are not existing behavior.
   Pass the real bounded health callback to `confirm` under the confirmation
   lease; do not evaluate it first and substitute cached success. Verify the backend
   reports the target good and primary, durably clear the pending trial, and
   only then remove `/run/sv08/trial`. The marker must remain if any write or
   verification fails.
5. On a positively validated target trial with failed OS health, persist the
   failure and preserved generation/log location, then invoke one reviewed,
   bounded orderly fallback path. This path must validate the target slot,
   transaction ID, boot ID, and backend context before requesting a reboot.
   The reboot consumes the existing finite U-Boot trial attempts (the reviewed
   RAUC policy currently pins three); it must never re-arm, replenish, or reset
   the target counter. Once U-Boot selects the preserved source, reconciliation
   performs the pinned source/cancel path; if both slots are exhausted, leave
   the device for the documented recovery path. Ordinary source-boot errors,
   malformed state, missing config, and unknown
   outcomes must fail closed without reboot. A watchdog may participate only as
   a separately reviewed fallback mechanism. Do not call `Transaction.cancel`
   from the target slot: its contract requires the preserved source boot.
   On the next source boot, reconciliation returns `needs-cancel`, and the
   coordinator calls `cancel` after revalidating the source.

The unit ordering must make the existing Klipper condition evaluate after a
successful coordinator run: the proposed Klipper unit has
`Requires=sv08-prepare.service sv08-boot-health.service`,
`After=sv08-prepare.service sv08-boot-health.service`, and retains
`ConditionPathExists=!/run/sv08/trial`. Additionally require `ConditionPathExists=/run/sv08/os-health-ready` on
Klipper. The coordinator writes that volatile boot-local marker only after
successful validated nontrial reconciliation or durable trial confirmation.
Do not put skip conditions on the health unit. `Requires=` alone does not turn
a condition-skipped dependency into failure; the explicit marker closes that
case. A failed/skipped coordinator cannot release either gate. The existing missing-`printer.cfg`
condition remains valid. Moonraker is not claimed to be trial-gated; its
host-only `provider: none` mode may run after prepare for diagnostics, subject
to its own config condition, without starting Klipper or printer output.

This slice confirms host boot viability and safe A/B disposition. It does not
claim printer readiness or printing safety. The separate printer gate remains
responsible for config, MCU versions, sensors, outputs, homing, heaters, and
motion. This separation is required by [`docs/design/host-os-ab.md`](../design/host-os-ab.md),
which also requires preserving the failed slot's logs and user artifacts.

## Exact coordinator contract

The coordinator consumes the existing boot record and transaction API, but it
must independently validate the record because `boot.json` has no schema field.
Before any transition it must establish all of the following:

* `boot_id` is the current kernel boot identity from
  `/proc/sys/kernel/random/boot_id`, not a persistent machine ID.
* `slot` agrees with `rauc.slot=` in `/proc/cmdline` and with the RAUC backend's
  observed booted slot.
* `release` and state schema agree with the installed release manifest and the
  matching state-registry slot/generation.
* The generation path is the expected, non-symlink path and the persistent
  data, boot, and root devices pass the existing manifest checks.

The public dispatch boundary is:

```text
run(boot, transaction, os_health, boot_admission, fallback)
    -> "idle" | "staged" | "needs-arm" | "awaiting-reboot" |
       "needs-health" | "needs-cancel"
os_health(boot, stable_for_seconds) -> True
fallback(boot, transaction_id, reason) -> recorded orderly reboot request
```

`run` calls `reconcile` once. `needs-arm` calls `arm` once through normal
staging admission; `needs-health` calls
`confirm` with the real `os_health` callback through the non-stopping boot
admission, and `confirm` owns its exactly-once evaluation; `needs-cancel` calls
`cancel` only from the validated preserved source boot. `idle`, `staged`, and
`awaiting-reboot` are classifications, not reasons to reboot. No coordinator
branch directly calls RAUC, U-Boot, `mark_good`, `mark_bad`, or a bootloader
command.

The proposed unit uses fixed executable paths, root ownership, no user
arguments, bounded output and a bounded runtime. It must not require
`sv08-klipper.service`, `sv08-moonraker.service`, `printer.cfg`, or an MCU to
start. It must retain the current
`ConditionPathExists=!/run/sv08/trial` gate until confirmation has durably
completed. Failure logs go to a bounded persistent journal under the selected
generation/shared diagnostics path and survive fallback; no log cleanup may
remove the failed target's evidence before review.

## Failure cases and acceptance IDs

| ID | Condition | Required result |
| --- | --- | --- |
| HBH-01 | Missing/malformed boot record, unknown field, boot ID mismatch, or invalid generation | Refuse before transition; retain gate and bounded diagnostics; no reboot. |
| HBH-02 | Cmdline slot, RAUC observed slot, state slot, or installed release/schema disagree | Refuse before bootloader work; preserve both slots and logs; no reboot. |
| HBH-03 | `reconcile` returns `needs-arm` | Arm exactly once through staging admission; never replenish an armed trial. |
| HBH-04 | Target trial has no printer config, no MCU, or no Moonraker printer provider | OS health may still pass; Klipper remains gated, while host-only Moonraker diagnostics may run; no printer readiness is inferred. |
| HBH-05 | OS health check fails, times out, or is unstable during the target trial | Keep gate; persist reason/generation evidence; invoke fallback only after positive trial/context validation. |
| HBH-06 | Boot admission for target `reconcile` or `confirm` cannot be acquired or accidentally invokes service-stopping admission | Refuse the transition; tests must prove the injected boot admission reacquires neither state/writer lock and calls no Klipper quiesce/stop. |
| HBH-07 | `confirm` or backend mark-good fails after OS checks pass | Keep gate and journal in retryable confirming state; do not report success or reboot on an unknown outcome. |
| HBH-08 | Source boot after target fallback returns `needs-cancel` | Revalidate source slot/release/boot ID, disarm target, then clear pending state through `Transaction.cancel`. |
| HBH-09 | Ordinary source boot, missing access point/DHCP, missing MCU, or absent printer config | Diagnostics remain available; no reboot loop and no trial failure is inferred. |
| HBH-10 | Required resource, output, journal, or stable-window bound is exceeded | Fail closed with bounded diagnostics; preserve the gate and do not silently retry. |
| HBH-11 | Early `sv08_boot.py` generation/state copy is interrupted or loses power | The next boot uses the existing journal and generation markers; incomplete copy/migration blocks confirmation and preserves source state. The coordinator only tests and consumes this handoff; it does not own the copy. |
| HBH-12 | Failed trial fallback requested without a positively validated target trial | Refuse fallback/reboot; preserve evidence for recovery review. |

## Focused verification

Extend existing tests before hardware work:

* [`tests/test_host_boot.py`](../../tests/test_host_boot.py): independent boot
  ID/cmdline slot/manifest/state validation, trial-marker retention, generation
  and bounded-log handling, nontrial no-reboot behavior, and rejection of
  malformed `boot.json` without assuming a schema field. Include the
  early-boot-to-coordinator handoff for a complete and incomplete generation
  copy; do not assign the copy operation to the coordinator.
* Add a focused test module alongside that test for `HostHealth`: fresh image
  with no printer config/MCUs, required host checks, stable-window timeout,
  missing access point/DHCP, malformed service evidence, and bounded output.
  Assert that no Klipper quiesce socket, heater, motion, configuration, or
  printer-readiness call is available to the OS callback.
* [`tests/test_transaction.py`](../../tests/test_transaction.py): add a real
  call-order test proving staging may use service-stopping admission, while
  target `reconcile` and `confirm` use the distinct non-stopping boot
  admission, which reacquires neither state nor writer lock;
  retain failed-health, confirming-journal, fallback, exhausted-attempt, and
  late-write coverage.
* Update the existing composed QEMU fixture
  [`tests/test_host_qemu_rauc_composed.py`](../../tests/test_host_qemu_rauc_composed.py)
  to exercise OS-only A→B confirmation with no printer config/MCU and one
  failed target-health fallback. Keep `physical_hardware=false`; this is
  disposable composition evidence only.
* Run only these focused nonprivileged tests and unit-file/static checks. Do
  not run a release build, flash, SSH, hardware session, or printer readiness
  test for this intake.

## Physical consumers and evidence reuse

H02 consumes true cold/warm boot, host OS health, A/B transitions, and distinct
boot IDs. It must start serial logging before reconnection, account for
serial/USB back-power, and inspect the current installed slot and environment.
H07 consumes controlled power interruption, exhausted/bad trials, watchdog and
recovery outcomes using expendable data. Neither H02 nor H07 can be closed by
offline or QEMU evidence, and H07 must keep power interruption separate from
heating and motion.

Reuse the public conclusions from [host environment tests](../hardware/host-environment-build.md),
[RAUC backend evidence](../hardware/host-rauc-backend.md), [rollback boots](../hardware/host-rollback-build.md),
and the [board image record](../hardware/host-board-image.md). These establish
software composition, transaction/RAUC behavior, and disposable or diagnostic
boot paths. They do not establish connected-board identity, DRAM reliability,
printer service health, physical fallback, MCU presence, or print safety.

Do not place private captures, credentials, machine serials, raw hardware
measurements, or generated artifacts in this intake.
