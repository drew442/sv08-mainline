# One guarded recovery return attempt

2026-09-29. Target: test-sv08-01, owner-reported H616_JC_6Z_V1.2. This bounded
[approved correction](../features/sd-recovery-reboot-guard/record.json) addresses
the [failed readiness followed by reboot](host-managed-sd-transfer-20260929.md).
Offline code and fixture tests do not establish keyboard response, SD return,
current boot counters, warm RTC retention or any supported printer behavior.

The [guard](../../scripts/sv08_recovery_boot_guard.py) defaults to inert inspection.
The coordinator uses its existing pinned-host-key SSH connections separately
to Beelink (`drew@beelink.drewnet.online` with fixed `sudo -n` before the guard)
and KVM (`root@glkvm`, without sudo). No new root Beelink login, Beelink-to-KVM
connection or credential transfer is added; failed noninteractive sudo stops.
No script downloads, build, media/environment writes, job/claim/writer-marker
arming or printer action occurs. The sole admitted attempt is
`sd-recovery-return-20260929-01`. An O_EXCL receipt consumes its primary attempt
before launching children, including an attempt that fails readiness. Keep this
same policy/receipt path: no new path to circumvent a consumed attempt.

## Live admission and the HID boundary

The existing [serial controller](../../scripts/sv08_serial_boot_route.py) preserves
its script/hash/countdown/capture and normal freshness gates. Its optional
readiness hook runs only after private capture reservation/fsync, exact UART
identity/topology, competing-descriptor checks and TIOCEXCL. A failed hook or
acknowledgment releases descriptors and sends no UART bytes. The exceptional
unknown-counter admission is explicit and requires this hook; it never sets
`fresh_environment_reviewed:true` without a fresh environment read.

The Beelink callback sends its actual PID, `/proc` starttime and executable,
UART and private capture descriptor/inode/owner/mode, topology, device number,
source hashes and fresh attempt nonce over the live SSH channel. The primary
validates that proof, sends one exact nonce-bound challenge/acknowledgment, and
requires a matching live response. Before that response the child rechecks its
process, parent, descriptors, source bytes, UART identity and capture fsync.
Primary child exit, stale/reused PID proof, malformed/replayed nonce, timeout,
failed callback or SSH loss forbids HID. Parent/SSH liveness is checked again
before each serial read/TX. Capture storage errors preserve the existing
controller's stop behavior.

The primary first prepares a separate KVM child, then obtains the live Beelink
acknowledgment immediately before the one HID fire message. Both SSH children
must still be alive at that boundary. This is a live bounded protocol, not a
fuser-only readiness claim. It cannot eliminate a process/hardware failure in
the interval after the proof; preserve an uncertain outcome and stop.

The KVM emitter checks the fresh `/dev/hidg0` descriptor is character `237:0`,
resolved `/sys/dev/char/237:0` is `/sys/devices/virtual/hidg/hidg0`, and the sole
gadget is `rockchip`. `functions/hid.usb0` must expose protocol=1, subclass=1,
report_length=8 and dev=237:0. `/run/kvmd/otg/hid.usb0@meta.json` must equal
`{"function":"hid.usb0","description":"Keyboard","endpoints":1,"order":0}`.
These were supplied measured read-only metadata, accessed 2026-09-29; they are
rechecked before every report, rather than treated as permanent device identity.

After the exact fire nonce/ack, only these four eight-byte reports are emitted,
with release reports explicitly included and no deliberate key hold:

| Report | Bytes (hex) |
| --- | --- |
| Ctrl-Alt-F2 | `05003b0000000000` |
| Release | `0000000000000000` |
| Ctrl-Alt-Delete | `05004c0000000000` |
| Release | `0000000000000000` |

There are no arbitrary keys, shell text, reset/power controls, retries or
additional report sequences. Partial/error writes or lost parent stop immediately;
no extra release is sent after an uncertain write. A missing release may leave
a key logically held. Four emitted reports are not proof of four received
keyboard events or exactly one actual reboot.

## Exact recovery source and the force/burst gate

The retained source recovery ext4 SHA is
`c83975508e1cafca51e23c6ad9e19408fa01b5d35be583b39a38c5b13ad2345c`.
Coordinator research reports `ctrl-alt-del.target` links to `reboot.target`,
whose ordered systemd-reboot.service has `SuccessAction=reboot-force` after
shutdown. No `/etc` unit overrides/masks or Xorg DontVTSwitch/-novtswitch were
found. These facts describe an ordinary CAD target with a final reboot action;
they do not establish a literally force-free path or measured keyboard response.
Kernel input handling, exact installed package/unit bytes and source revision
must be bound in the source receipt. Generic upstream defaults are insufficient.

The coordinator's independent approver clarified that the normal final
post-shutdown reboot-force is acceptable, while host autorepeat, default CAD
burst handling or a failed release can select an earlier forced path. Source
alone cannot prove event counts or rule out that risk for the emitted sequence.
The operational gate therefore requires a separately approved, exact pinned
risk-amendment digest, alongside the ordinary source/package/unit receipt and
immediate exact-operation review. It must explicitly accept the early-force/
stuck-release uncertainty and preserve jobs/claims/writer markers disabled.

The current v2 decision is pinned as canonical SHA
`d2a5dcd9cc8fc839a2c416305a8428e30bb2b194a8f98a975b982036c8bb613e`.
Source receipt `managed-cad-source-receipt.json` SHA
`e89460c6052d390bc328208e01db885e32165e5de693843caec3b6f06ab27c0d`
binds the exact recovery image, shared `/usr` SquashFS SHA
`ab8a0e8dd48a112f4c95e3b8cec43e62b424b230fc5195400af47269e2db2537`,
Linux 6.18.51 candidate Image SHA
`5bc7c62df2b521610d0dea0a82b38aceb54af7d340a44b02a27428d6ea28dc34`,
installed systemd 257.13-1~deb13u1 ARM64 package SHA
`dcc3ba37f0488ecd513820035b4efc300e198849f5b6437a9bac9c2f307149ab`,
and retained unit/link inspection SHA
`c70df852d92d0c3dbdd074cb5524d343e196338d805818e50d90d796a1174dbd`.
The receipt identifies actual kernel keyboard/reboot source hashes and Debian
source metadata; it does not claim the source archives were newly downloaded.
Primary systemd references are [v257.13 manager code](https://github.com/systemd/systemd/blob/v257.13/src/core/manager.c)
and [burst configuration](https://github.com/systemd/systemd/blob/v257.13/man/systemd-system.conf.xml),
accessed by coordinator research on 2026-09-29. No extra source retrieval ran here.

The gate requires these exact source bindings and the v2 risk digest, normal
final reboot-force acknowledged, early-force risk accepted, and event/reset
counts explicitly unproven. Missing or changed bindings refuse apply/serve/HID;
inspection reports mapping readiness. Synthetic test approvals never authorize
operation. Immediate independent Sol/high operation review remains a separate
required receipt; do not assert `immediate_force_or_sysrq:false`.

## Independently surviving capture restoration

Before opening UART, Beelink serve starts a separate bounded transient systemd
supervisor (240-second runtime, 180-second controller-release wait). Its lifetime
does not depend on primary SSH or a Python finally block. It observes the actual
controller PID/starttime exit/reuse, checks actual UART descriptor release and
exclusive-open availability, closes its receive-only probe descriptor, then
**recreates** a fresh bounded receive-only transient unit using systemd-run.
It never sends HID/UART bytes, changes termios/control lines, reboots, retries
boot or kills an unknown UART user. If ownership remains uncertain, it stops and
requires coordinator recovery rather than stealing the port.

The exact existing no-argument collector is pinned at SHA
`5c4e6cd4f1e8039949c83654c1265ffad51c269230268ca445e4491d7bf2b0ed`,
with the reviewed argv `python3 /home/drew/sv08-captures/sd-recovery-host-20260929/capture.py`.
It uses O_RDONLY/TIOCEXCL and its existing 115200 raw/CLOCAL/no-HUPCL setup,
with its original 12-hour/50-MiB console counter, appending console.raw/events.jsonl.
That source counter alone does not bound events.jsonl; tiny reads can grow the
event log much faster than console data. The recreated unit now explicitly sets
`LimitFSIZE=4194304` and `Restart=no`. Linux enforces an absolute 4 MiB size cap
on each regular output file, including existing appended bytes; reaching a cap
stops collection on write failure rather than automatically relaunching it. The original
collector does not share the controller's advisory lock; restoration does not
claim it does. An existing old collector must have been explicitly released by
the coordinator before apply; the guard does not stop unrelated units. Recreated
units have fresh nonce-specific names and `--collect`, rather than trying to
start a removed transient unit. Existing evidence is retained, not overwritten.

Before launch, each existing console.raw/events.jsonl must be strictly below
4 MiB and their combined size strictly below 8 MiB. Files are neither rotated,
truncated nor overwritten; reaching the budget is a stop requiring coordinator
review. The two collector files can total at most 8 MiB, plus the controller's
1 MiB UART capture, about 1 MiB of runtime source and finite small receipts,
well below the 64 MiB aggregate budget. Check current sizes and space before the
physical review. No full image copy or build scratch is needed.
Permission errors, persistent descriptor owners or systemd launch failure remain
explicit stop conditions; supervisor logs and the primary receipt must be retained.

## Coordinator policy and offline validation

Primary policy binds `attempt`, existing `beelink_host`/`kvm_host`, fixed
`remote_script`, `beelink_policy`/`kvm_policy` and exclusive `attempt_receipt`
paths, plus the reviewed serial policy and mapping receipt. All remote argv
paths/host tokens reject shell syntax; SSH uses BatchMode and StrictHostKeyChecking.
It reuses existing authentication without reading/copying private keys.
Beelink uses only fixed noninteractive sudo; KVM uses its existing root login.
Runtime dependencies are Python 3 standard library, existing SSH/sudo/systemd-run,
the two guard/serial scripts, existing scripts/sd_boot_route.py,
scripts/build_sd_recovery_host.py and runtime/sv08_gpt.py. Preserve their module
layout on both hosts; no installer/package/authentication changes are needed.

Serial policy keeps `fresh_environment_reviewed:false`, ordinary capture/MMC
identity fields and an explicit `recovery_return_exception`: format
`sv08-one-recovery-return-v1`, exact attempt ID, original approval digest,
v2 `risk_amendment_sha256`, exact-operation-review SHA, and true counters_unknown/rtc_retention_unknown/
jobs_disabled/claims_disabled/writer_markers_disabled. The original approval
binding is the canonical decision SHA
`93f021c0fb801551d88d3ae04dc9683ee29092fe80d3f8872662d5227cfd10ea`.
Mapping evidence separately binds recovery/kernel/systemd-package/unit-chain
hashes, review SHA and the approved v2 risk-amendment SHA; it cannot claim event or
reboot count proved. Beelink policy also supplies existing script/boot.cmd/
composition, fresh capture, fixed collector path/hash and no collector args.
KVM policy binds only `/dev/hidg0`, a fresh private `hid_receipt` path and the
same accepted source/risk receipt. Each report's exact bytes, write result and
elapsed syscall time are flushed to that exclusive receipt. Partial/error results
remain retained; receipt failure stops further reports. Primary completion checks
and retains all four successful per-report results without inferring host response.
Keep private device IDs, host names and policies in ignored paths.

```sh
python3 scripts/sv08_recovery_boot_guard.py --policy local/reviewed-guard.json
python3 -m unittest tests.test_sv08_recovery_boot_guard tests.test_sv08_serial_boot_route -v
```

The default command performs no SSH, serial, capture creation or HID writes.
`--apply` is coordinator-only after independent delivery verification, matching
amendment/source gate and immediate Sol/high exact-operation review. Internal
--serve/--hid-serve/--supervise modes are launched through that fixed protocol;
they are not instructions to invoke hardware from this offline handoff.

47 focused offline checks have passing evidence: the 21 guard checks passed
after this resource correction, and 26 unchanged serial checks reuse their
accepted evidence. These cover guard entrypoint ordering and failed/dead/stale/
malformed/PID-reused readiness, exact ack/timeout/SSH loss, source gate and
freshness refusal, real private capture hook checks, four-report/partial-write
HID transport, fresh metadata drift, pinned collector recreation/budget, and
actual disposable controller-process exit after its input channel closes before
supervisor recreation. Fixture subprocess/HID transports replace physical
interfaces; the actual guard/readiness/supervisor functions execute. The resource check executes the exact pinned collector source in a disposable
Linux subprocess with a real 4 KiB RLIMIT_FSIZE and hardware-only transport
fixtures. One-byte UART reads exhausted events.jsonl while console data remained
below the limit; the process exited with EFBIG, released its descriptor and sent
zero UART bytes. Existing prefix bytes were retained. Launch-argv checks require
the production 4 MiB limit and Restart=no; this offline check does not claim an
actual Beelink systemd unit was exercised. Unchanged
loader/writer/build/QMP evidence is reused. No hardware command ran for delivery.

Current redundant counters, RTC retention, keyboard response, new-loader SD
routing and actual reboot count remain unknown. Missed interception, inherited
script reset, timeout or failed SD return stops; no second attempt. If SD SSH
returns, first read/validate both redundant environments and compare Linux/RTC
time before staging, signed-job preparation or another reboot. Before operation the coordinator and immediate reviewer must bind the identified
installed spare, retained factory baseline, independent SD/USB artifacts,
PSU-off/printer-disabled state, no armed writer job/claim/marker and no incomplete
whole-device transfer. Factory rollback does not prove spare persistence cannot
be corrupted. Missed interception can enter a normal slot, consume attempts and
make persistent writes that burst reset might interrupt. Any newly introduced
irreplaceable spare data requires its existing authorized preservation evidence;
stop if those premises, preservation or target authority are not established. Physical H12
return remains a separate requirement. Retirement: supported authenticated
recovery reboot and boot selection; no release or printer commissioning claim.
