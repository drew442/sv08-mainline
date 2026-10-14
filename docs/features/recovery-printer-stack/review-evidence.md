# PR17 review implementation and measured blocker

Owner-selected [review5525165502](https://github.com/drew442/sv08-mainline/pull/17#pullrequestreview-5525165502), implemented at **f79192d54e3e765095d3bd1c511e7e4d1830d70c** on a current-main integration of the preserved PR17 candidate. [Plan](review-plan.md), [numeric results/source hashes](review-evidence.json). Original f57123c [evidence](evidence.md) and its JSON remain byte-identical; no historical receipts refreshed.

## Implemented fixes

- host_assert keeps Moonraker API and real key stat in distinct variables. Complete mocked successful HTTPS/SSH/CA/auth path with an actual temporary-file stat produces the intended Moonraker receipt; protections remain.
- Actual production validation caps each connect/send/receive and sleep by remaining ten-second budget and checks time again before accepting ready. Fragmented/late responses, shutdown/error, failed private sinks and TERM/KILL cleanup have outcome regressions. AS268435456, CPU soft/hard8/8, file-size4194304 and pinned entry/dictionary remain unchanged.
- Opt-in bounded private telemetry captures actual PID, applied limits, child CPU through isolated RUSAGE_CHILDREN with Popen as sole reaper, virtual memory, actual cgroup event availability/deltas, bounded progress/I/O samples, API state/socket and pre-cleanup exit plus cleanup signals. Up to32 samples and8192 bytes per log tail; default callers do not publish raw logs/state messages.
- Explicit arm64-kvm supports normal/recovery roles, requires native LinuxARM64 and actual KVM initialization, refuses functional clock/fallback, and verifies active QMP accelerator with modern/older interfaces. TCG remains separately identified; image hashes, media identity, one writable target, read-only source disks, owned QMP, restricted loopback forwarding and recovery nic:none are tested.
- Current-main compatibility repair unifies prospective and actual Cockpit identity socket bytes and its exact source provenance recipe, preserving PR20 qualification/notices.

Root-executed source-bound checks: **186 run,185 passed,1 existing pinned local-parser skip**; focused69 (one skip) in3.537seconds and recovery/export/restore/activation/image/printer staging117 in68.583seconds. Actual real ARM64 production parser was exercised separately below and failed; neither a skip nor offline PASS closes full qualification. Final code hashes match recorded test snapshots with no source drift.

## Isolated unchanged-limit measurements

Coordinator verified retained root/initrd/kernel hashes, then built a small diagnostic-only initramfs with fresh staged helper/probe/factory source, read-only retained normal root and one64MiB private result disk; no networking, PID1/service/Identity provisioning or printer access. Current helper invocation, installed old-helper identity, Python/module/catalog/dictionary/entry/complete input hashes are recorded separately. This is an isolated configuration measurement, not a normal boot acceptance or final image.

First input reached Klipper util.create_pty but the minimal guest lacked mounted devpts. Actual validator exited1 after5.294 childCPU seconds, parent5.570seconds, no cleanup signals; missing PTY setup was established from the private traceback. It is not the historical SIGKILL cause. One diagnosed fixture correction mounted devpts and repeated identical source/configuration/clock/pins/limits. Failed input and64MiB result disk retained.

Corrected measurement:
- Guest childPID230; **SIGKILL/-9 before cleanup**, no TERM/KILL sent by validator.
- Reaped childCPU **7.987973seconds** (user3.228004/system4.759969); observed CPU soft/hard8/8. Parent guest readiness elapsed **8.953544seconds**, below ten.
- Observed peak virtual memory44540KiB (43.5MiB), RSS29624KiB. Actual AS256MiB and file-size4MiB limits observed.
- API socket appeared, last operationrecv, no completed API state.22 bounded progress samples showR/Z and wchan0.
- Actual root cgroup membership observed, but memory.events/local unavailable; empty counters mean unknown, not zero. Guest kernel log available with no OOM/PID-correlated OOM line; absence does not universally rule out OOM.
- Host QEMU elapsed46.016seconds /46.192 CPU seconds is distinct from child guest accounting. Live QMP verifiesTCG underQEMU8.2.2; requested icountshift0,alignoff,sleepoff/two vCPUs/1024MiB unchanged.

This strongly supports a hardCPU-budget failure in the **new isolated TCG run**. Historical SIGKILL causation remains unestablished. Measurements do not show the review's conditional I/O/deadline-advance pattern; no sleep=on comparison or blind clock retry was performed. No timeout/resource limit was raised.

Both probes cleanly stopped; wrapper exit0 is not acceptance. Retained normal root remainsSHA80fce114f10b876df2e8699bd09ce5857f19ae65a2e8b31f0c85684dc1e940c3. Raw configuration, excerpts, stderr and kernel logs remain root-private under /root/.sv08-recovery-review-20261014. Published JSON contains reviewed numeric measurements/hashes only.

## Remaining concrete blocker and next execution

Codex and Beelink arex86_64. Actual new native preflight on Codex refuses with nativeLinuxARM64 required; no already allocated authorized ARM64/KVM runtime has been identified. Native activation is **not exercised**, not passed. No allocation/spending was authorized. Full source boot/export, installed restore/activation, two distinct restored boots, strict TLS/authenticated browser/SSH, rollback/previous boot remain unqualified. Existing image builds predate the final fixes; do not reuse them as final acceptance.

On an approved nativeARM64/KVM host: initialize the explicit backend, observe enabledKVM through liveQMP and retain command/version receipt; restage/rebuild both final images including all reader/validator/driver changes; execute the existing six acceptance checks and complete normal/export/recovery/activation/reboot/rollback/browser journey. Keep PR17 draft/unqualified until it actually passes. GenericARM64 success still is not H616 timing, physical rescue media, MCU/printing qualification.

## Accounting and authority

Original10800seconds/48GiB charged conservatively in full. Review continuation3600seconds/8GiB gives14400seconds/56GiB cumulative; all failed/retired inputs and attempts carried forward. Review conservative charge1300seconds/1GiB includes185 passing checks, skip, both probes, record/merge/setup and unmetered reserve; worker32seconds/130MiB included. Total conservative12100seconds/49GiB. Codex24GiB/Beelink25GiB free at intake; no large OS image copies/rebuilds, only small initramfs/results disks.

One native named project_implementer, medium requested/fork_turns=none, no delegation or settings changes. Coordinator owns source integration, root/VM execution, stable-diff/result inspection, records and publication. Effective model/effort not independently observed; no independent-review or savings claim. No printer, heaters/motion, live host changes, installs, merge or deployment. Native recovery goal remains paused; owner-selected review work is tracked in the existing project task records.
