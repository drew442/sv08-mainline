# H12 actual preflight candidate, 2026-09-30

An actual preflight-only candidate is prepared from accepted
[node-binding delivery](host-h616-emmc-node-binding.md). This advances
[H12](host-network-emmc-h12-intake.md); physical urh-04/05 remain open.
H616_JC_6Z_V1.2 remains owner-reported.

## Actual inputs and checks

Preparation used main `6246cb1a9a44285cb1ba99f1c34a859781af6d6a`, containing
accepted source `9d98550d91eb3396f6debd0ee5e03196530c0723`.
Read-only intake at 23:09:57 UTC confirms the same SD boot and installed-spare
controller/CID hash, `/dev/mmcblk2` device179:8 and capacity31,272,730,624 bytes.
Linux and RTC agree within approximately one second. This is warm readback;
physical board identity and cold clock retention are not established.

Fresh distinct Ed25519 job and receipt keys are for preflight only. The unchanged
job preparer streamed the existing Beelink raw v5 source: 7,818,182,656 bytes,
SHA-256 `ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.
Job `a46735b7ce7ee9ab7e25a00e0312ae18` expires **2026-09-30 23:47:37 UTC**.
Claim state is prepared and unserved. Expiry requires a fresh job/artifact;
this candidate must never be rearmed or reused after expiry.

The actual trusted-initramfs/recovery-handoff writer contains signed v2 policy
and preflight purpose. Composition used retained pinned kernel/initramfs/DTB.
Shared verification extracted and checked the compiled selector and FIT members,
then verified executable purpose, job signature, policy and embedded initramfs
inputs at the selected persistent artifact. Both exact private signing-key PEM
values are absent from its archive; private keys were not supplied to composition.

| Selected member | Bytes | SHA-256 |
| --- | ---: | --- |
| `writer.itb` | 48,901,632 | `15ef085c90896e0fea3f146290611fefe5e43adf59d05dd43c0c54bc8d087235` |
| `writer-initrd.img` | 15,446,785 | `96197aa534f3856923ed107ac49d967cf74d261fdeabac7c4a1364e6f983414d` |
| `Image` | 33,405,440 | `5bc7c62df2b521610d0dea0a82b38aceb54af7d340a44b02a27428d6ea28dc34` |
| `sv08.dtb` | 48,208 | `571288762747007542bb00c7ce04c2e0994678422e441975d928022588da9d3f` |

Build manifest SHA-256:
`a42a6c87e9829f0897f3a8ffece2f6c41543056031e91afbdb5647743d43aeb0`.
Uncompressed archive is54,858,752 bytes. Conservative static working memory is
565,513,633 bytes against **assumed**1 GiB. Kernel `[0x40080000,0x4205ba00)`
and FIT `[0x48000000,0x4aea2e00)` intervals do not overlap each other or fixed
marker/script addresses. Physical RAM availability and relocation remain untested.

## Preserved failures and resource evidence

An incomplete remote source closure failed before job/state creation; read-only
reconciliation confirmed that absence. Exact missing tracked imports/configs
were added without production changes. Local finalization subsequently failed
after remote job success; it was corrected locally without rerunning preparation.

Initial FIT composition exhausted local disk space. Its partial artifact and
logs remain preserved. Exact compressed/uncompressed archive equality was proved
before removing only new duplicate expanded/archive intermediates. Successful
composition used bounded512 MiB local tmpfs. Persistent selected hashes were
verified before scratch cleanup and unmount; identical regular members share
inodes with the preserved partial. Unique retained preparation allocation is
98,746,368 bytes, within the original128 MiB allowance. Exact transient peak was
not individually measured.

Independent high-consequence review refused the first volatile transfer plan:
the bundle location violated the source's ignored `local/` guard, and direct
binary PATH bypassed reviewed library wrappers. No transfer ran. The corrected
layout uses `source/local` and reviewed command wrappers; full shared verification
passes from an isolated unchanged source closure. A reviewer diagnostic then
exhausted host space by duplicating the artifact. Per-file failure hashes and
allocation were preserved before removing only that new duplicate. Review
continues against the original artifact in place, with bounded small scratch.

## Capture and physical gates

The existing receive-only collector was restored after independent
`high_consequence_reviewer_high` PASS WITH CONDITIONS, with actual GPT-6.1
Sol/high confirmed. Complete root process/FD visibility and fresh postchecks
confirm exact source/UART topology, sole read-only owner, active unit,12-hour
runtime,4 MiB per-file cap and Restart=no. Original disconnect reopen behavior
and termios changes remain; application receive-only access does not prove
electrical inactivity. Recheck immediately before boot. The
[capture mechanism](host-recovery-reboot-guard.md) defines these bounds.

At this preparation boundary no claim listener, p5 staging, environment arming,
activation, printer boot or full-image write occurred. The
[workspace](host-h12-workspace-20260930.md) and
[tools](host-h12-runtime-tools-20260930.md) remain preparation evidence.
Exact action authorization, current physical setup, fresh target/GPT/environment/
p5 checks and immediate independent reviews are required. urh-04 must establish
FIT entry, bounded read-only admission and original recovery return before a
separately authorized urh-05 full write/readback/next boot.

Sources accessed2026-09-30: accepted tracked tooling and ignored receipts under
`local/feature-workflow/probes/h616-physical-preflight/h12-access-20260930/`,
including physical-artifact-verification.json, retained-resource-measurement.json,
fresh inventory, capture review/postchecks and volatile transfer reviews.
Private identifiers, keys, raw dumps and artifacts remain ignored.


## Reviewed volatile transfer result

The corrected volatile transfer received PASS WITH CONDITIONS from the separate
`high_consequence_reviewer_high` agent. Runtime observation confirms GPT-6.1
Sol/high, full access and approval never. Its independent probe rehashed27inputs
and passed full actual artifact/signature/policy/purpose/archive verification
using unchanged accepted source. The failed original candidate remains preserved.

Immediately before execution, exact sender/receiver/manifest/input hashes and
all restored tool hashes/modes were rechecked. One strict enrolled SSH transfer
installed98,738,504 bytes in a fresh root-private tmpfs directory. Actual
on-printer artifact and signed-stage verification passed; SSH exited zero.
Stderr contained the existing sudo hostname-resolution diagnostic; it did not
prevent execution. No hostname configuration was changed.

A separate fresh read-only postcheck confirmed all27files are regular, root-owned,
mode0600, single-link and exact size/hash; directories are0700. Root remains
ext4 `ro,norecovery` on179:2; `/tmp` remains256 MiB tmpfs on0:24 with its existing
flags. Free `/tmp` is169,627,648 bytes and MemAvailable758,902,784 bytes. Synchronous
transfer/verification processes exited; these inert files are volatile. No p5,
environment, marker, claim or boot action occurred.

Fresh shared GPT checks pass both headers/arrays, all six signed partitions and
SPL/environment exclusions. Both raw environment copies remain CRC-valid and
byte-identical to intake, A counters3/2 and B0 with no arm token. A fixed1024-byte
read of the actual p5 ext4 superblock reports state1 and no pending journal replay.
This read does not establish broader filesystem integrity.

The first prospective p5-stage script received an independent high FAIL because
its writable mount preceded signed GPT/kernel partition admission. It was never
executed. The separately preserved revision adds full read-only map admission
and read-only no-replay original-script/free-space inspection before any writable
mount. It has a separate review pending. Its sender requires an actual owner
response authorizing this p5 file/metadata write and confirming current physical
setup; neither the active goal nor address-based key trust supplies that authority.
Staging, environment arming, activation and boot remain separate operations.
