# H616 writerless adapter: offline candidate

Status: offline implementation and synthetic QEMU integration complete;
independent delivery review pending. Date: 2026-09-26. Hardware profile:
test-sv08-01, reported PCB `H616_JC_6Z_V1.2`; this report contains **no new
physical measurement or write**. The H10 read-only probe identified one
61,079,552-sector `MMC` under `4022000.mmc`, but did not capture a fresh CID
comparison or bind that CID to an opened descriptor. See the
[H10 report](host-sd-network-emmc-probe-20260926.md) and
[readiness audit](host-network-emmc-reimage-readiness-20260926.md).

The default [SD/NFS diagnostic builder](../../scripts/build_sd_network_image.py)
is unchanged and still builds only the read-only probe. The explicit
[`h616-commissioning` builder](../../scripts/build_h616_reimage_candidate.py)
creates a synthetic-test NFS-root directory with a static ARM64 init, job,
signature, local target policy, expected image hash and a manifest. Physical
candidate construction is currently refused because no public reviewed record
binds an exact physical image hash to its disk GUID. The builder emits no bootable SD
image, boot script, claim server or automatic trigger. Its manifest says
`nondeployable-commissioning-candidate` and `physical_target_validated: false`.
It refuses construction unless a fresh empty output and four private 0600
inputs exist under the worktree's ignored `local/`: canonical target policy,
public Ed25519 verifier, canonical signed job and detached signature. The
policy contains the locally expected CID, `4022000.mmc` controller, `MMC`
type, 61,079,552 sectors, `/dev/mmcblk0`, expected `dev_t`, board-compatible
string, claim-server address and exact image hash/GPT map. None of those target
identity fields comes from the network job. The six partition names, offsets,
sizes and physical PARTUUIDs are derived from the reviewed host layout and
test-sv08-01 board profile. The synthetic test map additionally requires its
exact disk GUID, six PARTUUIDs and pinned image hash; a wrong but internally
consistent policy and signed job are refused. A physical image hash/GUID pair
must be independently reviewed and pinned before physical candidate assembly
can be enabled. The signed job binds the policy
hash, 7,818,182,656-byte read-only NFS source, its SHA-256, validity window,
and the same six-partition map. Real CID and signing material have not been
provided to this work and are not included in the source or this report.

The shared [writer](../../tests/fixtures/sd-network-root/emmc_image_writer.c)
selects H616 only when built with the explicit commissioning define. The
physical branch requires both the locally pinned board-compatible string and
`allwinner,sun50i-h616`, read-only NFS root, and the exact commissioning
command-line token. Before opening `/dev/mmcblk0`, it checks the pinned bundle
hashes and signed-job time window, requires a successful one-shot claim
response, opens and validates the source, and hashes the complete source image.
Only after that hash matches does it recheck target identity and open the target.
The H616 adapter scans the `4022000.mmc` sysfs inventory for one MMC of the
expected CID/type/sector count, checks the controller path and expected
`dev_t`, and compares the card inventory's device number with block sysfs.
It opens the target once and compares `fstat(st_rdev)` with that same number.
It rechecks the inventory and dev number before the first
write. The same descriptor is used for the complete write, flush and full
readback. Any refusal or uncertain write ends in a poweroff path; there is no
retry or rearm code in the guest. The server-side durable claim is the existing
[`ClaimState`](../../tests/sv08_emmc_job.py) implementation.

The [QEMU harness](../../tests/host_qemu_sd_network_emmc_write.py) now has an
explicit `--commissioning` switch. It compiles the same H616 adapter/writer
with a synthetic policy and the public test key, maps a synthetic MMC inventory
to disposable QEMU USB storage, and uses the same one-shot service. Its small
compile-time test exception accepts QEMU `virt`, substitutes QEMU's USB target
path and skips the physical controller realpath assertion; a physical
commissioning build has none of those exceptions. The harness still uses a
fresh regular-file target in a private network/mount namespace and performs
independent host SHA-256 and both-GPT/partition checks after a full run. This
synthetic model cannot establish the H616 kernel's actual CID/controller/dev_t
mapping.

Initial offline checks on the original implementation revision (historical;
the source and binary hashes in this subsection are superseded by the review
retest below):

```text
python3 -m unittest tests.test_h616_reimage_candidate tests.test_qemu_reimage_mode tests.test_sd_network_emmc_write tests.test_sd_network_image -q
31 tests passed (15.59 s; original implementation revision)
aarch64-linux-gnu-gcc -static -Os -D_FORTIFY_SOURCE=2 -Wall -Wextra -Werror ... emmc_image_writer.c
physical and synthetic H616 compile checks passed
python3 -m py_compile scripts/build_h616_reimage_candidate.py tests/host_qemu_sd_network_emmc_write.py tests/test_h616_reimage_candidate.py
passed
git diff --check
passed
```

The local tests cover missing/changed/stale/incorrectly signed job inputs,
exact 0600 private input permissions, wrong but mutually consistent policy and
job GPT fields, output-parent symlink refusal, unchanged default diagnostic,
deterministic synthetic artifact construction, and a native execution of the H616 identity
adapter against single, changed and ambiguous synthetic inventory. Additional
regressions assert the H616 fixture's exact 61,079,552-sector inventory across
all three identity faults, and pass the H616 target capacity through both host
admission checks and the success receipt. Existing
QEMU-mode and writer regressions also passed. The synthetic artifact built
from the fixed public test inputs in `tests/test_h616_reimage_candidate.py`
has writer SHA-256 `723ca2d058408471b01c2f626aba2cfac4d019b5e8e8c94fa446eb748cc50af4`
and ARM64 binary SHA-256
`49602427e3520438f08e3a0355ce6ae92594cfbf9e39fedb0332f1e1f0c5d28a`.
The original builder, QEMU harness and H616 test source hashes are respectively
`03fd74de5bc43d6116eeb4822ac89f7f5ba69876f678b661edd0a1c1769b8b73`,
`5d31e20940364e4e67ad8ae19e3e7b136ac09dd5ab17482b7a3712df3b42b64c`,
and `060b0a6259c3df60db5d908e0d972338a419790e9a2371eb7dd1068db3260436`.
The synthetic policy/job/signature/verifier hashes are respectively
`61814a3ee45841e4d082fc0318dd10f130f21dab54b20c60650f7d7438b2149b`,
`172c6da19a532b81e27eaf8ef09a65d3641ac4c7a47548292592ca26e21532e7`,
`1bbc394529e124c4f1f6cd3afe25b59727fa5270a3bac4ce3ad1d42a8d3c28dd`,
and `ee3b19c1538b4ce509616e4dc44f697161095ab1d2c0b3f1b0c26589f44cf434`.
These are public test identities and **cannot authenticate a physical job**.

The initial synthetic H616 QEMU transfer and fault matrix ran on Beelink; its
historical record is
[the original QEMU evidence record](host-network-emmc-h616-adapter-qemu-evidence-20260926.json).
After independent delivery review identified missing guest coverage, the
updated writer and harness were retested against the same SD composition and
extracted
NFS packages from the prior
[QEMU-mode run](host-network-emmc-reimage-mode-qemu-20260926.md), in a bounded
network/mount namespace, with a fresh disposable regular-file target per case.
The full run transferred and independently re-read the complete 7,818,182,656
byte source. Guest and host readback hashes matched; `sgdisk -v` validated both
GPT copies, and disk GUID plus all six partition records matched. The expected
61,079,552-sector (31,272,730,624-byte) target capacity was reported.

All three identity faults (wrong CID, wrong `dev_t`, ambiguous inventory)
refused before modifying the target. The before-write injected fault also left
the target unchanged. Partial-write, flush and readback injections wrote only
the first 1 MiB, which independently matched the source prefix; each consumed
the one-shot claim, rejected replay with HTTP 409 and emitted no success receipt.
The flush and readback injections exercise their respective post-write paths on
that 1 MiB prefix only, not after a complete image transfer. Full-run time was
43:07.79 (maximum RSS 2,311,932 KiB); fault-case times and receipt hashes are
in the evidence JSON. One guest `GFP_ATOMIC` warning appeared in the full run;
there was no OOM or NFS failure.

The updated ten-case retest (full transfer, four identity refusals, three
source refusals, lost claim acknowledgement, and abrupt interruption) is
recorded in
[the review retest record](host-network-emmc-h616-adapter-review-retest-20260927.json).
Its ignored raw-result directory is
`local/integration-evidence/network-emmc-h616-writerless-adapter-review-retest/`;
the raw summary SHA-256 is
`6f650a7847b29b66500846089caa8a23d0129961c8066e7e0ae5e65fffdca20a`.
The four tested source hashes are recorded in that public record. The abrupt
case verified the full source before target open, wrote and fsynced the first
MiB, and then the host sent SIGKILL to QEMU. The first MiB matched the source;
the durable one-shot claim rejected replay with HTTP 409 and no success receipt
was produced. This is an abrupt synthetic VM termination, not physical power
loss. The four identity and three source refusal cases plus lost acknowledgement
left the target prefix unchanged, consumed the claim, rejected replay, and
produced no success receipt. The full transfer took 42:46.41 (maximum RSS
2,310,848 KiB); the wrong-hash refusal took 17:15.04 and abrupt case 16:51.44.
Each of the full and abrupt runs emitted one guest `GFP_ATOMIC` warning, with no
OOM or NFS error. Beelink had 10,715,668,480 bytes free before and
10,706,477,056 bytes after the run; no raw image was staged on the development
VM.

The submitted source hashes are builder
`67884c15601eb6b5238833359e3d4bcc5e248968f89603573d282114a94267e3`, writer
`47ab15717b2a1f11bc7716e7dab8bc70fd947849e23339b70d364870aeeb9015`, QEMU
harness `6a9ce6a2a2823071f2fc30cdd6114529d245e23bd9d691acd15a84a7e25d1dab`,
and H616 tests
`d366757c57a920af8d8ec721e2440f34fb123c972b82bfd51ad34ddfcde2c1af`. The
full retest manifest binds the built ARM64 writer hash
`539085d22757b3e1db8baab8c932c27940ad794d4af00dc459dc9df449453a9d`; these
values supersede the historical implementation hashes above. The coordinator
reran this current focused suite:

```text
python3 -m unittest tests.test_h616_reimage_candidate tests.test_qemu_reimage_mode \
  tests.test_sd_network_emmc_write tests.test_sd_network_cid_admission \
  tests.test_sd_network_image -q
37 tests passed (15.78 s)
```

The independent verifier also reproduced focused tests and a strict static
ARM64 build. Python compilation, JSON validation, workflow validation, and diff
checks passed for the submitted source and evidence.

These results establish only synthetic QEMU integration. The exact command
shape for reproduction is:

```sh
sudo unshare -n -m -- python3 tests/host_qemu_sd_network_emmc_write.py \
  --work /private-scratch/fresh-h616-case \
  --sd-work /private-scratch/verified-sd-composition \
  --package-root /private-scratch/extracted-nfs-packages/root \
  --commissioning --execute
```

The initial matrix recorded above used each of its original identity/fault
options, plus the no-fault `--commissioning --execute` transfer, each with a
fresh claim and disposable target. The updated ten-case matrix is separately
bound by the review-retest JSON. The harness generates the sparse 7.8 GB nonbootable source
and verifies its pinned hash, so no physical image or private backup is
included. Beelink had more than 10 GB free before and after the runs and over
7 GB available memory. No raw image was staged on the development VM.

Physical candidate construction is blocked until the selected image's exact
SHA-256 and disk GUID are independently recorded together. The plain HTTP claim transport, port supplied in boot arguments, independent
SD boot image, and real NFS export/trigger have not been reviewed as a physical
trust chain. In particular, a physical claim acknowledgement is not yet
authenticated to the printer; QEMU's isolated network does not resolve that
gap. The candidate remains inert and nondeployable. Before H12 can be run,
the project needs a fresh live CID and `dev_t` map, exact image/policy inputs,
a reviewed one-shot boot/claim transport, power-loss and USB-writer recovery
procedure, independent high-consequence review, and explicit action
authorization. Reuse [H12](coordinated-human-tasks.md) as the single physical
commissioning task; no new human media swap is requested here. The custom
writer/adapter exists only to fill the missing whole-eMMC identity and
one-shot path; retire it if a supported upstream mechanism meets that contract.
