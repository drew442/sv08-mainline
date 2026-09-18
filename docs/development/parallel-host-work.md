# Parallel host integration and release work packet

Planning baseline: 2026-09-18. This is a source-backed coordination packet for
the host work that can proceed while printer access is intermittent. It does not
authorize a hardware write, a production activation, or a supported-release
claim. The coordinator should merge this packet into the cross-cutting index in
[parallel work](parallel-work.md) and keep physical handoffs in
[coordinated human tasks](../hardware/coordinated-human-tasks.md).

The completion checklist is the authority for status; this packet groups its
unchecked work into bounded owners and names the evidence that can be reused.
Offline evidence is not upgraded to physical or release evidence. In particular,
the diagnostic image has reached A, recovery, SSH and Cockpit, but its changing
DRAM result, lack of physical display observation, and masked printer services
remain explicit limitations ([board image](../hardware/host-board-image.md),
[host checklist](../hardware/host-os-tasks.md)).

## Bounded offline work

| Slice | Owned boundary and deliverable | Reuse and offline acceptance |
| --- | --- | --- |
| Board boot and health composition | Render one reviewed board profile into the host, recovery and boot-service inputs; wire boot-time reconciliation, health confirmation, fallback and watchdog outcomes. Keep the environment on the verified MMC index and refuse unknown board/layout identities. | Reuse [board recovery](../hardware/host-recovery-board.md), [A/B environment](../hardware/host-environment-build.md), [rollback](../hardware/host-rollback-build.md), and [RAUC backend](../hardware/host-rauc-backend.md). Add ARM64 service tests for A→B→A, exhausted/broken trials, late state copy, failed health and recovery dispatch; retain the hardware and power-loss gates.
| Assembled update coordinator | Connect authenticated upload, transaction reconciliation, idle admission, configurable automatic staging, next-boot arming, opt-out, customization refusal and controlled idle reboot. Keep application software update paths disabled when image-managed. | Reuse [transactions](../hardware/host-transactions.md), [update admission](../hardware/host-update-admission.md), [upload staging](../hardware/host-upload-staging.md), [image jobs](../hardware/host-admin-image-jobs.md), and [RAUC backend](../hardware/host-rauc-backend.md). Test service races: job start versus update, late writes, migration failure, no space/inodes, dropped browser, interrupted install and retry identity. No callback stub may be wired as production health.
| Administration and software/network adapters | Implement the reviewed catalog, dependency/space preview, admitted APT operations, service configuration, customization reconciliation, owner onboarding, persistent account/SSH/TLS identity, NetworkManager forms, hostname/hosts publication, connectivity rollback and idle restart. | Reuse [administration UI](../hardware/host-admin-ui.md), [Cockpit integration](../hardware/host-admin-cockpit.md), and [bundle upload](../hardware/host-admin-upload.md). Use disposable ARM64 roots and real PAM/sudo/Cockpit sessions; verify malformed input, rollback and persistence. Leave network association, visible UI and credentials on the human gate.
| Finite image-job history | Separately scope bounded receipt rollover without evicting unknown outcomes or losing retry identity; reuse completed job-resolution delivery. | Start from `runtime/sv08_admin_jobs.py` and `tests/test_admin_jobs.py`; preserve the 128-receipt bound and demonstrate capacity/retry/unknown-outcome behavior before independent review. |
| Independent recovery integration | Dependency for the separately owned recovery-export composition. Keep host integration scoped to the consumer contract and its boot/service handoff; downstream signed restore and user-data restoration remain future-scoped recovery work. | Reuse [recovery image](../hardware/host-recovery-image.md), [media admission](../hardware/host-recovery-media.md), [export](../hardware/host-recovery-export.md), and [readback](../hardware/host-recovery-readback.md) as supplied by recovery delivery. Do not duplicate its export implementation or claim physical USB, touch or restoration until the recovery owner and attended gates complete.
| Host/MCU compatibility gate | Produce a machine-readable compatibility check binding the selected host package, Klipper/Moonraker/Mainsail/KlipperScreen revisions, both MCU artifacts, board profile and calibration scope. Refuse activation on mismatch and document that OS rollback does not roll MCU flash back. | Reuse package and MCU provenance from [host stack](../hardware/host-stack-build.md), [kernel packages](../hardware/host-kernel-packages.md), and the named `test-sv08-01` MCU build records. Test version mismatch, missing MCU, partial Katapult transition and rollback bookkeeping with simulated devices. Hardware identities and electrical behavior stay unknown until commissioning.
| Reproducible release assembly | Finish independent rebuilds and manifests for remaining packages/wheels; harden the recovery-intake completion receipt against concurrent lock replacement; then assemble signed boot/root/recovery/data artifacts from clean inputs and measure the complete factory-sized layout, update workspace, state-copy allowance, inode reserve and licenses. | Reuse [factory-capacity baseline](../hardware/host-ab-build.md), [kernel compile/package records](../hardware/host-kernel-compile.md), [board image contract](../hardware/host-board-image.md), and the accepted 512 MiB recovery allocation. Require clean repeated builds, input/output hashes, source/license manifests, `dpkg --audit`, `apt-get check`, filesystem checks and full 8 GB occupancy tests. A capacity fixture or diagnostic image is not a release.

Each slice should have one implementation owner and an independent delivery
review. Keep `upstream/` pinned and place project changes in `configs/`,
`runtime/`, `scripts/`, `patches/` or `tests/` with provenance and retirement
criteria. Heavy builds should use fresh ignored `build/` directories and record
toolchain, source pins and hashes; this packet itself changes documentation only.

## Human dependency mapping

Human actions are canonicalized in [coordinated human tasks](../hardware/coordinated-human-tasks.md).
Use the existing IDs below; do not create another backup, writer-transfer or
power-isolation request. Each consumer records its result against the H ID and
reopens it only when the coordinated-task invalidation rule applies.

| Host consumer | Required human task IDs | Boundary and sequencing |
| --- | --- | --- |
| Board boot/health and first-print path | H01; H03 only if needed before candidate boot; H02; H04; H05; H06 | Establish board/sensor identity, capture a true isolated boot, observe peripherals, pass input gates, then proceed through staged outputs and printing. This is the priority path ahead of broad administration work. |
| Physical A/B, fallback and release recovery drills | H02, H03 when reinstallation is required, H07 | Reuse one reviewed candidate and one capture-ready session; keep power interruption separate from heating/printing. H07 also consumes recovery delivery's export/restore result when that work is ready. |
| Administration, network and camera acceptance | H04, with H02 as its boot baseline | H04 supplies one physical console/peripheral session covering normal and recovery input paths, Wi-Fi, USB and sustained camera behavior. It does not certify a different image or recovery UI. |
| Modified printer commissioning and host/MCU activation | H01, H02, H05, H06 | H05 establishes sensor/input identity and H06 gates outputs, homing, heaters and prints. Version compatibility remains an offline prerequisite; physical success does not qualify stock support. |
| Supported stock release and publication decisions | H07, H08, plus the completed offline release assembly | H08 supplies license/omission decisions and actual stock access; H07 supplies controlled failure evidence. Modified-printer results remain separate evidence. |

Recovery export and downstream restore are owned by recovery delivery. The host
packet consumes their reviewed interface and evidence through H07; it does not
duplicate those actions or add backup prerequisites.

## Next actionable offline assignment

The next bounded assignment is **assembled update coordinator**, after the board
boot/health composition is ready enough to define its health contract. The core
transaction semantics already exist in [`runtime/sv08_transaction.py`](../../runtime/sv08_transaction.py):
`stage()`, `stage_upload()`, `arm()`, `reconcile()` and `confirm()` have unit
coverage in [`tests/test_transaction.py`](../../tests/test_transaction.py) and
staged-upload coverage in [`tests/test_staged_transaction.py`](../../tests/test_staged_transaction.py).
The RAUC/device and idle-admission components are also implemented in
[`runtime/sv08_rauc.py`](../../runtime/sv08_rauc.py) and
[`runtime/sv08_admission.py`](../../runtime/sv08_admission.py), with assembled
guest evidence in [`tests/host_qemu_rauc_backend.py`](../../tests/host_qemu_rauc_backend.py)
and [`tests/host_qemu_admission.py`](../../tests/host_qemu_admission.py).

The actual gap is the production coordinator boundary: wire boot-time
reconciliation and the independently supplied health callback, expose the
already authenticated upload path through
[`runtime/sv08_admin_images.py`](../../runtime/sv08_admin_images.py), and add
the service-owned scheduler/idle-reboot policy around the existing transaction
methods. [`runtime/sv08_admin_jobs.py`](../../runtime/sv08_admin_jobs.py)
explicitly has no scheduler or reconciliation, while
[`runtime/sv08_boot.py`](../../runtime/sv08_boot.py) intentionally fails closed
until OS health confirmation is integrated. Extend the existing focused tests
(`tests/test_admin_jobs.py`, `tests/test_admin_images.py`,
`tests/test_host_boot.py`, and `tests/test_host_qemu_rauc_composed.py`) for
late-state writes, job/update races, opt-out, customization refusal and failed
health. Do not reimplement the transaction, RAUC backend or complete image
assembly. Keep the assignment offline, with no printer, private credentials,
hardware writes or heavy release build.
