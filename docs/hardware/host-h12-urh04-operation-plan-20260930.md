# H12 urh-04 physical preflight operation plan

Prepared2026-09-30, **not authorized or executed**. This is one host-only physical
preflight on the installed spare in test-sv08-01. It advances the existing
[H12 gate](coordinated-human-tasks.md), using the
[actual candidate](host-h12-preflight-candidate-20260930.md). Board revision
H616_JC_6Z_V1.2 remains owner-reported. No media move is planned.

## Exact candidate and target

- Installed spare: controller4022000.mmc, MMC type, capacity31,272,730,624bytes,
  current `/dev/mmcblk2` device179:8. CID SHA-256
  `08d24eb0a58bc7288c07020a0432586ea6070b78abdd86b209de362c7b42fe8a`.
- Recovery p5: device179:13, PARTUUID `b28438ed-f895-4b93-9bad-d27d3890ccd3`,
  offset4,714,397,696bytes, size536,870,912bytes. Signed six-partition v5 map
  uses backup GPT at7,818,182,656bytes, not physical capacity end.
- Original720-byte recovery.scr SHA-256
  `57e414bec126a309085f3e2be211c6b8fe0e43f5833a5b5609f3e69457808dee`.
- Actual preflight FIT48,901,632bytes SHA-256
  `15ef085c90896e0fea3f146290611fefe5e43adf59d05dd43c0c54bc8d087235`;
  manifest SHA-256
  `a42a6c87e9829f0897f3a8ffece2f6c41543056031e91afbdb5647743d43aeb0`.
- Job `a46735b7ce7ee9ab7e25a00e0312ae18`, expires2026-09-30 23:47:37UTC.
  Keys/job purpose are preflight-only. Expired inputs cannot be armed, booted or
  reused. A replacement requires fresh signed inputs/artifact and exact review.

Owner action permission must explicitly cover the p5 metadata/files, redundant
environment preparation, marker activation and one controlled boot/return below.
The project goal and SSH-key trust do not supply this permission. Current PSU-off,
USB-serial host power, Ethernet, installed spare/stored factory module and absence
of new irreplaceable spare data must be confirmed. Each operation also requires
its immediate independent high-consequence review and fresh admission. Passing
one operation is not authorization or acceptance for the next.

## Separate operations and observations

| Phase | Intended operation | Required result before continuing |
| --- | --- | --- |
|1. Stage files | Validate exact source/artifact/job, pinned target descriptor, signed GPT and kernel p5 geometry/PARTUUID; inspect p5 in private read-only/no-replay mount. Require clean ext4, original script hash, no existing stage and FIT+16MiB reserve. Then privately mount p5 writable without replay, preserve original script, copy FIT and atomically install checked wrapper; fsync and unmount. | Wrapper/FIT/original hashes match; stage journal reports wrapper-durable; both environment records remain byte-identical and no armed marker exists. |
|2. Prepare environment | Re-admit the same target/mount/job/staged journal. Use accepted `arm_live_target` and reviewed fw_setenv wrapper on the opened target descriptor. Set BOOT_ORDER=A B, BOOT_A_LEFT=0, BOOT_B_LEFT=0 and sv08_reimage_arm=exactjobID in both64KiB copies at4MiB/8MiB. | Both CRC-valid copies have the exact job token and exhausted counters; unrelated fields are retained. Record raw before/after privately and stop on any uncertain copy. |
|3. Activate | Recheck signed inputs, staged files, target and both armed environments with accepted `activate_live_target`; publish only the checked sv08-reimage/armed marker last and fsync. | Marker-durable journal, exact marker bytes, unchanged FIT/original hashes and expected armed environments. Cleanly unmount before boot. |
|4. Admit services and boot | Revalidate Beelink source/export; start the supported expiring one-shot claim server on192.168.1.136:12000 using this private root-owned job state. Verify actual live listener/source/expiry without issuing a claim. Recheck the surviving bounded UART collector. Execute one separately reviewed ordered SSH reboot; allow the installed managed loader's standard eMMC route. | Observe actual U-Boot/FIT entry, trusted initramfs, stable controller/CID mapping, durable marker consumption, NFS/read-only source and signed one-shot receipt. No blind reboot or claim retry. |
|5. Observe preflight and return | Compiled preflight code opens the admitted whole device only read-only/exclusive after marker unmount, checks capacity and both raw environments, then requests automatic return. Retain capped serial output and observe original recovery GUI. | Actual PREFLIGHT_PASS/capacity/environment evidence, expected marker/claim outcome and original recovery return. GUI alone does not prove the read-only checks. |

The preflight executable excludes the full target transfer path at compilation;
it still performs the explicitly listed p5 marker metadata operation and consumes
one signed server-side claim. This is not a metadata-free test. It performs no
MCU, heater or motion commissioning. Actual RAM availability, FIT/DTB/initrd
relocation and unattended return remain urh-04 acceptance requirements.

## Stop and recovery

Any source/hash/clock/expiry/target/GPT/map/mount/clean-state/ownership/resource/
service/capture mismatch prevents the next operation. Any write, flush, timeout,
missing receipt, lost response or unexpected boot result stops without automatic
retry, rollback, rearming or further boot. Preserve original scripts, raw
preimages, staged journal and bounded captures; reconcile uncertain state read-only.
Private namespace teardown on process exit is not proof of recovery.

Independent SD rescue remains installed; the original SD composition and reviewed
loader preimage are retained. The factory eMMC remains stored with the accepted
USB-reader recovery path. Any physical recovery action needs its own identified
artifact, authorization and immediate review. Original recovery fallback protects
the boot path; it does not establish persistence or full failure-mode safety.

Whole-image urh-05 is a later, separately authorized attended operation **only
after actual urh-04 passes**, with complete transfer/flush/readback/GPT/next-boot
evidence. This plan grants no urh-05 authority or printing/release claim.

Sources accessed2026-09-30: accepted
[live adapter](../../scripts/live_h616_recovery_stage.py),
[stager](../../scripts/stage_h616_recovery_handoff.py),
[job/claim preparer](../../scripts/prepare_h616_reimage_job.py),
[writer](../../tests/fixtures/sd-network-root/emmc_image_writer.c),
[managed route](host-managed-boot-route.md), actual candidate/intake receipts and
[agent execution policy](../../.codex/agent-guide.md).
