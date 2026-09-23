# Boot-health composition: offline implementation evidence

Checked 2026-09-23 against the approved [proposal](proposal.md) and its
`hbh-01`–`hbh-12` checks. This is offline source and test evidence. No printer
write, board boot, physical fallback or release acceptance occurred.

The coordinator validates the prepared boot identity, selected slot, installed
release, registry generation and paired devices before a transition. A distinct
non-stopping boot admission is passed to target reconciliation and confirmation;
the existing staging admission remains in use for arming. Transaction retains
state-lock and writer ownership and evaluates the real OS health callback once
before mark-good. The 5-second stable interval has a 40-second callback budget
inside a 50-second process deadline and the service's 60-second timeout. A
stalled backend probe raises a coordinator deadline and retains a bounded
failure record when the initialized state store is available. Successful nontrial reconciliation or
durable target confirmation publishes `/run/sv08/os-health-ready`; Klipper also
retains its trial and private-config gates. Failed trial health records bounded
diagnostics and requests fallback only after renewed target/journal/backend
validation under the state, boot-admission and writer locks. An interrupted
final confirmation journal write is retryable only for the exact validated
target; it does not trigger fallback. A same-boot service restart clears an
old ready marker before reading fallible inputs. Full target confirmation still depends on the reviewed production
RAUC policy, layout and environment inputs in the final image.

The focused command
`python3 -m unittest tests.test_host_boot_health tests.test_host_boot tests.test_transaction tests.test_host_integration tests.test_stage_admin_ui`
passed 59 tests. Python compilation and `git diff --check` passed. Tests cover
malformed/mismatched boot records, writable nontrial and staged boots, target
confirmation and failure, unknown backend outcomes, missing printer/network
prerequisites, admission call order, unit ordering, installed enablement link,
interrupted confirmation, bounded RAUC observation and probe deadline,
complete/interrupted early-boot handoff, and existing transaction behavior.

The existing `tests/host_qemu_rauc_composed_run.py` VM fixture masks
`sv08-prepare.service` and synthesizes only a source-A boot record. It does not
exercise this service or a second target-B boot. A distinct two-boot persistent
fixture with reviewed update policy, layout and environment inputs is still
needed for disposable QEMU A→B confirmation and target-health fallback.
Physical cold/warm boot and fallback remain H02/H07 in the
[coordinated task queue](../../hardware/coordinated-human-tasks.md). These open
checks must not be inferred from the unit tests or the existing QEMU fixture.
