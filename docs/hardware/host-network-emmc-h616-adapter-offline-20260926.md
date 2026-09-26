# H616 writerless adapter: offline candidate

Status: offline implementation complete; full synthetic QEMU integration and
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
`allwinner,sun50i-h616`, read-only NFS root, and the explicit command-line
mode. Before opening `/dev/mmcblk0`, it checks the pinned bundle hashes and
signed-job time window, then requires a successful one-shot claim response.
The H616 adapter scans the `4022000.mmc` sysfs inventory for one MMC of the
expected CID/type/sector count, checks the controller path and expected
`dev_t`, opens the target once, and compares `fstat(st_rdev)` with the sysfs
device number. It rechecks the inventory and dev number before the first
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

Offline checks on the implementation tree:

```text
python3 -m unittest tests.test_h616_reimage_candidate tests.test_qemu_reimage_mode tests.test_sd_network_emmc_write tests.test_sd_network_image -q
29 tests passed (15.49 s)
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
adapter against single, changed and ambiguous synthetic inventory. Existing
QEMU-mode and writer regressions also passed. The synthetic artifact built
from the fixed public test inputs in `tests/test_h616_reimage_candidate.py`
has writer SHA-256 `eb99f1cf3566ff841702a4a9b96585ca6f5f7542242aecbe5ad4c3e7f0f1a5a6`
and ARM64 binary SHA-256
`5dd3d5fb8c6cb73b5b38ca3240d298690c7fdf613366343da7dc04a24af23b6e`.
The builder, QEMU harness and H616 test source hashes are respectively
`03fd74de5bc43d6116eeb4822ac89f7f5ba69876f678b661edd0a1c1769b8b73`,
`61c206e5cb18a97cf0df8f64210d032a74d5e26afe97e32d9449eb6b91ef6419`,
and `ba6ac4f0bd26d416d2a7e8f004a764a438a8e8063f35515cfc3735c89bc3c07a`.
The synthetic policy/job/signature/verifier hashes are respectively
`61814a3ee45841e4d082fc0318dd10f130f21dab54b20c60650f7d7438b2149b`,
`172c6da19a532b81e27eaf8ef09a65d3641ac4c7a47548292592ca26e21532e7`,
`1bbc394529e124c4f1f6cd3afe25b59727fa5270a3bac4ce3ad1d42a8d3c28dd`,
and `ee3b19c1538b4ce509616e4dc44f697161095ab1d2c0b3f1b0c26589f44cf434`.
These are public test identities and **cannot authenticate a physical job**.

The full synthetic H616 QEMU transfer, failure and replay matrix has not yet
run. The assigned integration worker should reuse the Beelink SD composition,
extracted NFS packages and bounded namespace from the prior
[QEMU-mode run](host-network-emmc-reimage-mode-qemu-20260926.md), with a fresh
work directory for each case. The command adds `--commissioning`:

```sh
sudo unshare -n -m -- python3 tests/host_qemu_sd_network_emmc_write.py \
  --work /private-scratch/fresh-h616-case \
  --sd-work /private-scratch/verified-sd-composition \
  --package-root /private-scratch/extracted-nfs-packages/root \
  --commissioning --execute
```

Run separate `--identity-fault wrong-cid`, `--identity-fault wrong-dev`,
`--identity-fault ambiguous`, `--fault before-write`, `--fault partial-write`,
`--fault flush`, and `--fault readback` cases as resource limits permit; each
uses a fresh one-shot claim and disposable target. The harness itself generates
the sparse 7.8 GB nonbootable source and verifies its pinned hash, so no
physical image or private backup is needed. Beelink must have at least 9 GB
free and 3 GiB available memory. No raw 7.8 GB image should be staged on the
space-limited development VM.

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
