# Assembled update and reboot reliability

This work closes controlled-restart admission gaps and ordinary healthy-boot counter
exhaustion. Evidence below concerns disposable ARM systems and native checks; it is not
physical printer, electrical power-cut or release qualification.

## Runtime behavior

Controlled restart writes a strictly validated, boot-bound shutdown intent before
requesting systemd restart. Managed printer/web service starts, image staging, package
operations, network mutations and operating-mode changes respect it. Accepted or
uncertain restart acknowledgment leaves services stopped and admission closed. Only a
proven command-launch failure removes the caller's own intent and restores admitted
services. Old-boot intents cannot block a new boot.

CLI and Cockpit mode changes share eligibility checks for transaction consistency and
pending or uncertain jobs. Image enqueue rechecks state under the state-before- ledger
lock order. Network restart records intent while serialized with state, network, storage
budget and printer admission. Managed systemd services use the same service-start gate;
the helper is staged in host and recovery packages.

Ordinary healthy boots now confirm the identified running slot under serialized state,
admission and backend-writer checks. Stable health and live boot/state/ service identity
must remain valid around confirmation. Confirmation replenishes only that slot,
preserves boot order and the other slot counter, and supports writable/customized roots.
Image-operation identity checks remain immutable by default. Unhealthy or uncertain
boots do not publish readiness or refill counters; failed trial boots retain bounded
attempts. The older diagnostic backend without complete paired-slot context publishes
diagnostic health without counter writes.

## Native checks

The final runtime/test closure passed 258 tests in 20.310 seconds. Set
`SV08_TEST_SCRATCH` to an existing private directory (mode 0700):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime:tests TMPDIR="$SV08_TEST_SCRATCH" python3 -m unittest test_restart test_service_admission test_host_state test_network_admin test_admin test_admin_images test_software_admin test_transaction test_admin_jobs test_package_policy test_web_stack test_stage_admin_ui test_staged_transaction test_sv08_feed test_host_boot_health test_rauc_backend test_rauc_service test_rauc_bootloader
```

The log SHA-256 is `5c8be8ab0f59d7b9d41618572c49c00a629722a5102d76f10b4899e0ed1dca55`.
The 89-file executed-input manifest SHA-256 is
`f0181f186bb9b43c22c46925eb69dd18c8c46e5ea921c0814ca306cb66d1695c`, bound to published
source `f67cdf77178e83f26e3cc48b1f8bf338d32e8feb`. Native service objects are simulated.
Independent targeted review reproduced the original delayed-reboot admission gap and
lost-acknowledgment failure, then found the ordinary-boot counter defect. All three were
corrected before final acceptance.

## Disposable ARM acceptance

| Accepted boot | Slot | Actual elapsed (s) | Result |
| --- | --- | ---: | --- |
| 1 | A | 407.092 | Source health, signed stage/arm, restart exclusion and uncertain ACK gate |
| 2 | B | 376.475 | Healthy update confirmation, late configuration/committed WAL, signed failed target stage/arm |
| 3 | A | 177.098 | Failed target attempt 1; gate closed |
| 4 | A | 175.571 | Failed target attempt 2; gate closed |
| 5 | A | 175.797 | Failed target attempt 3; attempts exhausted |
| 6 | B | 92.862 | Fallback; healthy generation/configuration/database preserved, running counter restored |
| 7 | B | 82.595 | Writable 1; package exclusion, actual SIGKILL snapshot interruption/retry and migration refusal |
| 8 | B | 77.169 | Writable 2; customization/identity preserved and counter restored |
| 9 | B | 77.895 | Writable 3; customization/identity preserved and counter restored |
| 10 | B | 76.786 | Writable 4; explicit B3→1 decrease, host consumption to 0, production health restored B3 |
| 11 | B | 204.279 | Failed ordinary health withheld readiness/refill at B2; same-boot healthy retry restored B3 |
| 12 | B | 78.248 | Immutable customized root; image-update refusal and actual low-space refusal |

All twelve accepted boots exited successfully and their log hashes match retained
receipts. There were fourteen actual boots in this fresh fixture lineage: six accepted
initially, a discarded Admission API fixture failure, five accepted in the first
continuation, a discarded tmpfs ancestry fixture failure, and the final accepted boot.
Both failed attempts remain explicitly failed. Hashed checkpoints verified the same
retained disk, boot environment, runtime inputs, prior logs/receipts and original
preservation baseline before continuation; no accepted boot or signed installation was
repeated. The first source-counter recovery belongs only to the retired superseded
fixture; none was used here.

The final receipt SHA-256 is
`3810dd24a84c197988af1efaac9a364091a7e39b9ed1d83ea4d5dbf18fe049ca`. It binds original
installed runtime `f67cdf77178e83f26e3cc48b1f8bf338d32e8feb` to fixture-only
continuation `655f2a6f33a151f1996c4d7c83d0c2247d184c10`, with 89-input manifest
`5cb67f4e2c77d1b034f9d5062265453129ae32ec02e1270501976ede2fdffe48`. All 65 installed
runtime/image inputs and root-construction logic were unchanged through the fixture
revisions. The final execution carries the after 11 checkpoint
`736b1e61a7d9e6c0fb7e9c62ca6f671f17db34f633a39dc555d867df8d65e425`, which retains the
earlier checkpoint and discarded attempts.

Machine/host identity, CA and SSH identity hashes survived the sequence. Failed
target-only configuration/database writes did not leak into fallback. The original GPT
header, relocated primary table, backup GPT and recovery hashes match the final receipt,
and the shared base hash is unchanged. The final capacity refusal observed 67,104,768
available bytes below the production 805,306,368-byte reserve on a real 64 MiB tmpfs
with private 0700 permissions, without publishing a generation or changing its registry.

 ## Reproduction and storage

`tests/host_qemu_reliability.py` accepts an explicit JSON input manifest containing
scratch, read-only base, kernel, initrd, native RAUC, candidate revision and source hash
manifest, exact packages and storage/runtime limits. Its CLI exposes `prepare-inputs`,
`construct`, `export-template`, `build-media`, `refresh`, `recover-source`, `bundle` and
`journey`. It has no private-host path defaults. The fixture scripts are in
`tests/fixtures/reliability/`. The runner serializes resources, uses private
regular-file mount namespaces, refuses existing canonical receipts and retains failure
logs. Terminal markers alone do not pass a run: it requires the expected marker and
successful actual VM exit, and rejects failure markers anywhere in the console.

Free space was checked on codex and beelink before image creation. One shared read-only
base and one live sparse GPT disk at a time were used, with sequential temporary slot
construction and two compressed signed bundles. Historic project images were left
intact. Limits were 6 GiB live allocation, at least 16 GiB host free space, 32 GiB
cumulative generated allocation, 5400 seconds cumulative process runtime and 4 MiB logs
per run. The cumulative ledger retains retired allocations and failed attempts; active
inode growth/rename does not charge the same live bytes again. A real filesystem
allocation check verified retained retired charges, growth, rename and replacement
behavior.

Final charged integration runtime was **4119.593/5400 seconds**. The cumulative
allocation ledger retained **29,846,790,144/34,359,738,368 bytes**, including failed and
retired artifacts and conservative overcharges from earlier diagnostics. The cumulative
allowance was explicitly extended 6→12→14→22→32 GiB after measured construction and
diagnosed repairs; process allowance grew 3600→5400 seconds. Live allocation stayed
within 6 GiB and host free space above 16 GiB. The ledger contains a labelled
conservative 600-second prior-runtime seed plus separately labelled
metadata/reconciliation bounds; these are not invented measured runtimes. A diagnostic
mistakenly counted a temporarily mounted read-only filesystem view as additional
generated files; that conservative charge was retained, not refunded.

After final hashes, idle leases, consumer and loop-device checks, cleanup retired only
the goal-owned GPT disk, both signed bundles and synthetic signing files. It reclaimed
**6,025,523,200 allocated bytes**, leaving **14,344,192 live allocated bytes** of
scripts/packages/logs/receipts and **34,067,333,120 host free bytes**. The cumulative
history did not decrease. The cleanup receipt SHA-256 is
`f5c1003256dac950de52885d8faf7ca3bf1b8faea33f73edc11404da2d86383f`. No VM, assigned
mount or loop device remained. Historic images, kernel/initrd and the shared base were
preserved. An initial cleanup preflight checked autoclear loop detachment too early; a
bounded actual detachment observation corrected that disposable invocation before
deletion. The failed preflight was retained.

 ## Limits

QEMU uses Linux/systemd and actual ARM RAUC installation, with explicit simulated
printer status and a Moonraker service stub. Slot selection reads and decrements real
redundant environment data through the fixture host driver; it does not execute board
SPL/U-Boot. Trial health failure is deliberately injected at the prepare-observation
boundary. Guest process interruption is not electrical power-cut evidence. No operation
on a live printer was performed: no printer reboot, package/mode mutation,
physical-media rewrite, image activation or output activation. Printing, MCU
communication, physical fallback/recovery and release qualification remain separate
requirements.

The first actual failed-trial preparation failed before publication. Native reproduction
against its archived source then demonstrated source SQLite sidecar mutation: even a
read-only connection created an empty WAL beside a closed WAL-mode database. The
original ARM console did not retain the detailed Python error, so the mechanism is
native evidence consistent with its preserved state. The correction opens only the
private copied database/WAL, uses exclusive clients to keep WAL indexes in memory, and
reserves sequential backup/destination-WAL workspace. Native checks sample actual
allocated files after SQLite operations using a large-WAL database; they do not
continuously measure internal transient peaks. Real source changes and insufficient
workspace still fail before publication.

The nondeployable QEMU fixture extends timing for emulation: coordinator timeout 180s
(production 50s), host-health timeout 120s (production 40s), and health-unit
TimeoutStartSec 240s (installed 60s). Stable-health duration remains 5s. These are
explicit fixture-only overrides; results do not qualify production timing or
performance.

Independent targeted source/evidence assessment reproduced the delayed restart and
lost-acknowledgment gaps, identified ordinary healthy-boot counter exhaustion, reviewed
corrections and checked final native/source/ARM bindings. Final workflow verification
binds the canonical submitted evidence list; it does not imply printer deployment.
