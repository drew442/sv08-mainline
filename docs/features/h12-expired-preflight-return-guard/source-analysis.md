# H12 missed-interception source analysis

2026-10-01. Source base `81c664099fea87bd5fa86a7303b2c4557ed51ebd`.
Separate `project_researcher` `/root/research_h12_missed_interception`, with
coordinator-observed GPT-6.1 Sol/medium, full-access/never. Source/evidence-only
inspection; no physical access, network, builds, artifact copies or experiments.
This is diagnosis, not scope approval, independent delivery verification or
exact-operation authorization.

Retained provenance supports conditional consequences of the unchanged failed
urh-04 staged chain, including exclusion of its whole-image writer branch. It
does not establish the current raw environment/marker/RTC or guarantee a bounded
physical return. Preserve the failed result and its alternative explanations.

## Branches

| Missed interception path | Source-supported consequence | Limit |
| --- | --- | --- |
| Invalid/default RAM environment | Default dispatch skips RAUC and loads p5 wrapper; old wrapper fails its job/layout/order/counter predicate and loads original recovery. No marker removal by selector. | Matches the failed UART observation, but predicates were not individually printed; current RAM and recovery success unknown. |
| Valid environment, zero eligible attempts | RAUC cannot select a slot; replenishment is disabled; wrapper follows. | Historical exhausted records are not current readback. |
| Valid environment, eligible A/B attempt | RAUC decrements and saves the counter before loading the slot script. Normal slot persistence and later dispatch resets are possible. | Slot, save destination, write effects and subsequent reset count unknown; early CAD force can interrupt persistence. |
| Wrapper predicate/marker/FIT validation fails, or bootm returns | Preserved original recovery script follows; selector does not consume marker. Original load failure stops/exits; recovery uses panic=10. | Fallback is not an unconditional successful or bounded return. |
| Preflight fails before successful marker consumption | C finalizer requests poweroff. Marker routine may already have mounted p5 writable. | Metadata/journal effects and marker deletion after partial failure remain uncertain. |
| Marker consumption succeeds, then expiry/claim/target refusal | Unlink, directory fsync, syncfs and successful cleanup set preflight_return_ready. Finalizer requests automatic reboot, including stale-job and claim refusal. | Expiry does not prevent preceding metadata writes. Durability and next boot selection are unmeasured. |
| Marker consumed and preflight passes | Whole target is opened O_RDONLY with O_EXCL; checks run, descriptor closes, reboot requested. | No physical preflight entry/pass was observed. |
| Next boot, marker genuinely absent and old chain unchanged | Wrapper marker load fails and original recovery follows; another preflight entry through that selector is prevented. | Marker absence is not measured. Deletion/flush/unmount failure requests poweroff; an interruption can leave retention uncertain. |

A single HID sequence does not guarantee one hardware reboot: CAD autorepeat,
failed release, default burst handling, dispatcher resets, kernel panic and
preflight automatic return are separate possible sources of resets.

## Primary source bindings

The actual staged wrapper predates the later environment-import repair. Use
historical composer `script_text()` at `9d98550d91eb3396f6debd0ee5e03196530c0723`
and retained compiled wrapper/command, not the repaired current composer, to
reason about this boot. [Default dispatch](../../../configs/host-os/sv08-default.env)
and retained pinned U-Boot `ece349ade2973e220f524ce59e59711cc919263f`
`boot/bootmeth_rauc.c:329,414` establish counter decrement/save-before-slot-load;
the latter source SHA is
`8a28ee4c4067005c365f8ba081e07970c3e0314c340a21b57c9aeef938534513`.
Actual-loader source extraction binds `board/sunxi/board.c:537` SHA
`f64ee273da194d47f286c8e139ff7b2c66b55be5bef90acc9b5bea79e880b826`
and `env/mmc.c:465` SHA
`06c0f57d46470c98a7b3500a6da88c6eed81e589064a70f0d34eaae43bd7c232`.
The separate local board.c whole-file hash differs; do not substitute it for the
actual-loader environment-routing extraction.

[Trusted PID1 composition](../../../scripts/build_sd_network_image.py) replaces
its ORDER with `exec /trusted-writer`, so trusted execution does not fall through
to NFS userspace. [Compiled-purpose verification](../../../scripts/build_h616_reimage_candidate.py)
binds actual ELF purpose to signed mode/job/policy. The [C implementation](../../../tests/fixtures/sd-network-root/emmc_image_writer.c),
SHA `5bcbde4c95e8de4043758c8b932b940b75e736adfd295993de99f8fffd98d894`,
consumes marker before timestamp/claim admission (line 653), selects reboot after
successful consumption (line 938), and compiles preflight_target in place of the
whole-write branch (main at line 1060). The preflight compilation excludes the
source-image hash, whole-target O_RDWR and bulk/environment-last transfer.

## Exact retained chain required for new admission

| Object | Value or SHA-256 |
| --- | --- |
| Failed job | 8bd9a5860bc40abf37f14e5011544d18, signed preflight purpose |
| FIT | 48902416 bytes; 71dff7451462e7739779e8770196444c48c6bcd61650fe197040a4479dd216e9 |
| Old wrapper | 1250 bytes; 8455db04a2538e8a44199b11be86a2642c837785fb458ff2032b0e7d48a9fbce |
| Original recovery script | 720 bytes; 57e414bec126a309085f3e2be211c6b8fe0e43f5833a5b5609f3e69457808dee |
| Build manifest | ed55f4f1fe73810017407a928d1157715ebc6610a4f030b0a439bd959fa2d4b6 |
| Actual artifact verification receipt | 394684411fb8360100542d838f6ad2609ffdc5666e044cb1469b476ee95e0c05 |
| Actual ELF | d165f5d4a037d1fe7cc7db110ecc7fcfb18058fcd54c51162ab9eec629bca096 |
| Compiled purpose | 75637eac32bc6ced984048593ee8859b4d36b290f766ba8975ebf5fd40077e54 |
| Initramfs | e8b2c8c4612a929bb965a244f16674f16e3fc01dc18792f17f8ac4c633a40e6f |
| Embedded archive | b087e2ff77cae0c0bd8ee7c5a8704d23d5c8ee4e9b0eb2b8ac7ea9c495526df8 |
| Installed managed SD loader | 350a941a7ec67b541308d235bffa4b937b8171f683f3e96b0c51dd32fab64544 |

Private durable stage/arm/activation reviews and result/readback receipts bind
these values to the staged chain. The boot boundary readback SHA is
`bffa0685d3877bf3db55603d66863d6798704d0338d7d169ce4a4a97c79c6450`;
failed-result SHA `36c1204d2972c7defde0b603e5c1267927f383e5b7b90e7d7825dd882356187e`;
historical service-expiry observation SHA
`fa24a4ff29f44d535a1b63bf2c978b3bab6b930fb20c4ef84a7b56cc32e9facd`.
Existing immutable kernel/package/unit/CAD source-gate bindings remain required.
The original recovery filesystem input hash predates p5 staging; it cannot be
asserted as the current filesystem hash.

This provenance conditionally excludes a whole-image writer for the unchanged
staged chain. It does not make legacy jobs_disabled/writer_markers_disabled
assertions true, prove physical marker absence or waive fresh live service/
listener quiescence, exact hardware review, preservation and target checks.
After a successful SD return, immediately reconcile both raw environments,
Linux/RTC and read-only p5 before preparing replacement inputs or another boot.
