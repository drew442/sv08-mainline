# H12 attended SD software execution evidence — 2026-10-03

Status: execution passed; independent delivery verification pending. Physical
session/write/manual normal boot remain pending under the owner’s reduced scope.
The [proposal](proposal.md) supplies the five offline checks and constraints.

## Candidate and focused checks

Runtime/composer candidate `dd080df` was composed from the preserved pinned
recovery root and existing public SSH/sudo package closure on Beelink. Test-only
fixture authentication was explicit. Runtime bytes did not change in the driver
repair `2b26b59`. Both candidates were committed and pushed before remote runs.
All ten owned paths were inspected, with no other source/mode/gitlink changes.

- Eleven backend tests passed: short writes and full byte range; No/absent/close/
  relaunch; serialization/duplicate refusal; stale descriptors and changing source;
  in-use/source-on-target refusal; flush/cache/readback errors; synthetic Linux
  controller/CID/dev_t/read-only mount/holder/capacity admission. Production rejects
  regular targets; the installed fixture explicitly constructs file admission.
- Seven composer tests passed, including rejecting stale runtime/drop-in usr cache.
- Eight native XTest GTK journeys passed locally after the final driver repair:
  refusal, keyboard No, Escape, close, pointer No, keyboard Yes, relaunch No,
  pointer Yes. Actual target bytes determine the result. Timeout cancellation
  now fails explicitly, rather than counting as a successful No response.
- Diff/cached checks, Python parsing, local documentation targets and agreement of
  all eight indexed gitlinks with upstream-lock.json passed. Upstream was unchanged.

## Actual installed ARM64 run

The [receipt](installed-evidence.json) contains exact source/artifact hashes,
service invocations, results, source/SD preservation and measured resources.
Fresh composition passed in 59.4 seconds with peak additional allocation
1,326,407,680 bytes. It retained the 512 MiB root, pinned board kernel/DT inputs,
existing masks and volatile mount bounds; no new dependency or full-image RAM
staging was added. Existing compressed usr cache was not reused.

Coordinator ran tests/sd_reimage_vm.py on Beelink against that image. The first
run reached installed wiring and source mount, then terminated on the shared
20-second SSH timeout during systemd reload. Evidence was retained. The same
implementer repaired the test command timeout and drop-in ordering. The final
run used a 480-second total deadline and guest commands capped at 90 seconds and
the remaining deadline. It passed in 303.2 seconds; QEMU exited normally through
QMP and was terminal before resources were reused.

The actual installed backend/UI/drop-in hashes matched the composition receipt.
The normal service started the production screen. Then the late temporary test
drop-in selected the explicit GTK fixture, verified from effective ExecStart.
All eight native cases passed using a read-only independent ext4 source and a
separate writable disposable target file. The accepted image range was replaced
and the trailing 512 bytes preserved. The driver restored production ExecStart,
relaunched it, checked target bytes remained unchanged, unmounted fixture disks,
and verified the complete SD/source artifact hashes unchanged. No empty/mocked
result or screenshot alone was accepted as success.

The VM had 768 MiB RAM; measured root usage was 302,908 KiB of 498,900 KiB,
/run 2,652 KiB of 98,304 KiB and /tmp zero of 65,536 KiB. Full memory snapshots
are in the receipt. Transfer buffers remain fixed at 1 MiB. The installed source
mechanism tested here is ext4; coordinator separately established NFSv3 read-only
source access on the already-running physical SD host, without new dependencies.

## Limits and remaining acceptance

This substitutes Debian 6.12.107 and virtio/file fixtures for the board kernel/MMC.
It proves installed software wiring and actual byte transfer, not physical CID,
block-cache/media durability, touch calibration, PSU state, hardware compatibility
or release readiness. Hardware block flush/readback and the actual accepted full
image still require the attended physical session. Existing source target checks
remain live at Review and immediately after Yes; no fixture path is selected by
production configuration. The diagnostic v5 image’s known host-product limitations
are not waived. A fresh independent verifier must inspect full diff and hashes;
this document is evidence, not self-approval.
