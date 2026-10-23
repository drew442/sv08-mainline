# From the current software to a working stock SV08

Baseline inspected: `6e7a424335ef8de63c34054654719e42c9956c50`, 2026-10-23.
Current repair acceptance and source-bound results live in the
[stock-readiness feature](../features/stock-printer-readiness/evidence.md).
This is the current handoff, not a second task queue. Physical results belong to
[H01/H02/H04/H05/H06](../hardware/coordinated-human-tasks.md) and their
[single commissioning session](../hardware/test-sv08-01-commissioning-session.md).

## What already works, and what still prevents printing

| Journey | Current evidence | Remaining work and owner |
| --- | --- | --- |
| Select factory hardware | Built-in factory assembly supplies 24 devices, board mappings, factory source settings and native homing/gantry/mesh behavior. [Factory definition evidence](../features/factory-sv08-definitions/evidence.md). | Confirm the actual fitted boards, bed, hotend, sensors and probe match the selected definitions. A modified machine is not a stock-hardware qualification. H01. |
| Generate a complete configuration | Full generation supplies closed Klipper includes, Moonraker/Mainsail settings and start/end, cooling, pause/resume/cancel controls. [Configuration scope](../features/complete-printer-configuration/proposal.md) and [installed export](../features/complete-printer-configuration/installed.md). | Actual MCU identities and measured calibration are target-specific. Sourced probe starting offset zero permits setup; it is not a measured offset and printing stays blocked until recorded. |
| Preserve calibration correctly | The baseline could restore an invalidated offset from definition instance values, and an old instance value could shadow an editor change. | This delivery fixes both representations, explicit clearing/default suppression and affected replacement paths, with regression/browser checks. It does not invent a measurement. |
| Save and apply configuration | Reviewed, drift-checked managed publication exists and leaves Klipper stopped. [Publisher](../../runtime/sv08_printer_publish.py) and [store](../../runtime/sv08_printer_store.py). | Save/export is not application; application is not service activation. Review the exact saved candidate and apply it while admitted services are stopped. No automatic output start is added. |
| Access Mainsail/Moonraker after boot | Durable web-service startup and authenticated installed operation were delivered. [Persistent stack evidence](../features/persistent-printer-stack/evidence.md). | Recheck the actual installed revision and connection during session preparation; historical installed evidence is not a present-host observation. This goal makes no new printer connection. |
| Start physical Klipper | The normal unit requires prepared state, restart admission, no trial and OS-health readiness. Diagnostic images deliberately retain printer/update masks. [Unit](../../configs/host-os/systemd/sv08-klipper.service). | Exact-target physical commissioning activation remains a separately reviewed operation. Managed publication alone cannot start it. Do not remove masks or fabricate a health marker to make this row pass. H02/H06 handoff. |
| Calibrate and retain probe offset | Mainline manual probe calibration and the existing Cockpit calibration field are supported. [Owner starting-offset decision](../features/complete-printer-configuration/calibration-decision.md). | Record the measured result in Cockpit, save, regenerate and publish stopped. Normal `SAVE_CONFIG` conflicts with the included managed probe setting; automatic ingestion is not implemented. The session gives the supported path. H06. |
| Validate motion, heat and printing | Actual ambient input observations and paired MCU communication exist for the named machine; no first-print acceptance is recorded. [Ambient scope](../features/sensor-default-commissioning/intake.md). | Physical input association/polarity, fans/stop, motor direction, homing/probing, heated behavior, calibration, first layer and print controls remain. H05/H06. |
| Install on an arbitrary factory machine | Packages and a complete captured-board diagnostic image passed software/source gates. [Actual-image evidence](../features/current-release-qualification/evidence.md). | There is no qualified generic stock printing image. The generic [stock profile](../../profiles/stock-sv08/profile.json) remains research; named board/boot and modified-printer results do not supply unknown stock hardware facts. Target boot/MCU compatibility and an independent recovery route must be established before installation. H01/H02/H04. |
| Update and recover | A/B healthy update and fallback have named-machine evidence; restore software is implemented. | Complete-stack restore/reboot/rollback remains the separate [ARM64/KVM blocker](../features/recovery-printer-stack/review-evidence.md). Do not repeat destructive recovery or forced fallback during first-print commissioning. |

## Autonomous closure versus physical dependencies

The source/configuration repairs in this delivery address an actual stale-calibration
printing risk, reliable measurement entry and clearing, stale current-factory tests,
and misleading old installation/commissioning guidance. Full generation, publication
and native parser checks protect the existing working paths. Earlier identity,
initramfs, TLS and web-startup failures have subsequent working evidence; they are
not reopened as new missing features.

The remaining activation/installation rows depend on a real target and a reviewed
hardware operation. They are not solved by setting `deployable:true`, unmasking a
service or creating `/run/sv08/os-health-ready`. The diagnostic finalizer/composer
correctly refuse that shortcut. This delivery preserves those checks. Before asking
for attended output tests, the coordinator must prepare the exact reviewed
commissioning launch/configuration and a usable stop/restore route for that target.
If that prerequisite is unavailable, the session stops before activation and records
the exact missing profile or integration dependency; it does not issue generic root
commands for the owner to improvise.

A stock definition is documented manufacturer configuration, not physical proof for
every production revision. The current named test printer has owner-reported bed and
hotend upgrades. It can qualify its correctly selected configuration, but cannot
prove factory heater/sensor behavior while those upgraded parts remain fitted.
Keep generic stock-release acceptance separate from named-machine first-print results.

Fine sensor calibration and proprietary pressure-based automatic offset calibration
remain owner-deferred. The session uses the selected factory conversion settings
when they match the actual hardware and the supported manual probe procedure. An
ambient comparison does not identify an unknown sensor or validate a heated range.
