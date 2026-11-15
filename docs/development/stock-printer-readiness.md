# From hardware definitions to a working configured SV08

Baseline inspected: `6e7a424335ef8de63c34054654719e42c9956c50`, 2026-10-23.
Current repair acceptance and source-bound results live in the
[stock-readiness feature](../features/stock-printer-readiness/evidence.md).
The [owner clarification](../features/stock-printer-readiness/follow-up-request.md) makes the configured printer the acceptance target. Definition/parameter contracts are checked with representative configurations and boundary cases; no exhaustive combination or unmodified-printer prerequisite is imposed.
This is the current handoff, not a second task queue. Physical results belong to
[H01/H02/H04/H05/H06](../hardware/coordinated-human-tasks.md) and their
[single commissioning session](../hardware/test-sv08-01-commissioning-session.md).

## What already works, and what still prevents printing

| Journey | Current evidence | Remaining work and owner |
| --- | --- | --- |
| Select factory hardware | Built-in factory assembly supplies 24 devices, board mappings, factory source settings and native homing/gantry/mesh behavior. [Factory definition evidence](../features/factory-sv08-definitions/evidence.md). | Confirm the actual fitted boards, bed, hotend, sensors and probe match the selected definitions. Use the definitions for the actual fitted parts, including modifications. This is the H01 identification task, not a requirement to restore factory hardware. |
| Generate a complete configuration | Full generation supplies closed Klipper includes, Moonraker/Mainsail settings and start/end, cooling, pause/resume/cancel controls. [Configuration scope](../features/complete-printer-configuration/proposal.md) and [installed export](../features/complete-printer-configuration/installed.md). | Actual MCU identities and measured calibration are target-specific. Sourced probe starting offset zero permits setup; it is not a measured offset and printing stays blocked until recorded. |
| Preserve calibration correctly | The baseline could restore an invalidated offset from definition instance values, and an old instance value could shadow an editor change. | This delivery fixes both representations, explicit clearing/default suppression and affected replacement paths, with regression/browser checks. It also prevents remapping from restoring the old controller identity. It does not invent a measurement. |
| Save and apply configuration | Reviewed, drift-checked managed publication exists and leaves Klipper stopped. [Publisher](../../runtime/sv08_printer_publish.py) and [store](../../runtime/sv08_printer_store.py). | Save/export is not application; application is not service activation. Review the exact saved candidate and apply it while admitted services are stopped. No automatic output start is added. |
| Access Mainsail/Moonraker after boot | Durable web-service startup and authenticated installed operation were delivered. [Persistent stack evidence](../features/persistent-printer-stack/evidence.md). | Recheck the actual installed revision and connection during session preparation; historical installed evidence is not a present-host observation. This goal makes no new printer connection. |
| Start physical Klipper | The normal unit requires prepared state, restart admission, no trial and OS-health readiness. Diagnostic images deliberately retain printer/update masks. [Unit](../../configs/host-os/systemd/sv08-klipper.service). | Exact-target physical commissioning activation remains a separately reviewed operation. Managed publication alone cannot start it. Do not remove masks or fabricate a health marker to make this row pass. H02/H06 handoff. |
| Calibrate and retain probe offset | Normal Klipper calibration and `SAVE_CONFIG` use a top-level calibration lane and an automatic, hardware-bound observer; optional manual fields remain available. [Owner starting-offset decision](../features/complete-printer-configuration/calibration-decision.md). | Perform the attended measurement, use `SAVE_CONFIG`, wait for restart and accepted synchronization, and verify the active result. Apply the new generated layout once before using native persistence on older managed configurations. Physical calibration and reference repeatability are H06 tasks. |
| Validate motion, heat and printing | Actual ambient input observations and paired MCU communication exist for the named machine; no first-print acceptance is recorded. [Ambient scope](../features/sensor-default-commissioning/intake.md). | Physical input association/polarity, fans/stop, motor direction, homing/probing, heated behavior, calibration, first layer and print controls remain as H05/H06 tasks. Reuse applicable completed evidence; record the configured printer and result. |
| Install a supported configured printer | Packages and a complete captured-board diagnostic image passed software/source gates. [Actual-image evidence](../features/current-release-qualification/evidence.md). | The delivered artifact is diagnostic, not an activated printing release. The [generic profile](../../profiles/stock-sv08/profile.json) still has unresolved boot/board facts. Confirm the target host/MCU compatibility and recovery route for installation (H01/H02/H04); this is independent of enumerating bed/hotend/parameter combinations. |
| Update and recover | A/B healthy update and fallback have named-machine evidence; restore software is implemented. | Complete-stack restore/reboot/rollback remains the separate [ARM64/KVM blocker](https://github.com/drew442/sv08-mainline/pull/17). Do not repeat destructive recovery or forced fallback during first-print commissioning. |

## Autonomous closure versus physical dependencies

The source/configuration repairs in this delivery address an actual stale-calibration
printing risk, reliable measurement entry and clearing, the failing legacy component
selector after factory definitions, retained private identity after remapping, stale current-factory tests,
and misleading old installation/commissioning guidance. Full generation, publication
and native parser checks protect the existing working paths. Earlier identity,
initramfs, TLS and web-startup failures have subsequent working evidence; they are
not reopened as new missing features. The dated research profile is physical
evidence metadata, not an inventory of missing software: native probe/homing
configuration is already implemented despite older unset planning fields.

The remaining activation/installation rows are target-specific execution tasks. They depend on a reviewed
hardware operation. They are not solved by setting `deployable:true`, unmasking a
service or creating `/run/sv08/os-health-ready`. The diagnostic finalizer/composer
correctly refuse that shortcut. This delivery preserves those checks. Before asking
for attended output tests, the coordinator must prepare the exact reviewed
commissioning launch/configuration and a usable stop/restore route for that target.
If that prerequisite is unavailable, the session stops before activation and records
the exact missing profile or integration dependency; it does not issue generic root
commands for the owner to improvise.

A built-in definition documents manufacturer configuration; third-party definitions describe modifications under the same supported contract. The named test printer has owner-reported bed and hotend upgrades. Commission it using the matching selected definitions. A successful print accepts that configured printer; it does not imply every possible configuration was physically tested, nor is such exhaustive testing required. Keep pending physical execution tasks separate from demonstrated software defects and test-environment failures.

Fine sensor calibration and proprietary pressure-based automatic offset calibration
remain owner-deferred. The session uses the selected factory conversion settings
when they match the actual hardware and the supported manual probe procedure. An
ambient comparison does not identify an unknown sensor or validate a heated range.
