# H616 selector: read the intended redundant eMMC environment

Requirement: restore the accepted recovery handoff and writerless preflight under
[existing handoff requirements](../network-emmc-unattended-recovery-handoff/proposal.md)
and the [H616 preflight contract](../../hardware/host-h616-physical-preflight.md).
This is a required H12 repair; optional feature development remains paused.

## Reproduction and source evidence

On 2026-10-01 the coordinator staged, armed and activated the actual preflight
job and obtained separate read-only postchecks. One reviewed ordered reboot
loaded the 1,250-byte wrapper and immediately loaded its preserved 720-byte
original recovery script. UART reported two bad-CRC/default environment loads
from MMC(0). No preflight FIT or PREFLIGHT_PASS appeared; the server claim remains
unused. This attempt does not satisfy urh-04. Preserve all artifacts and evidence.

Pinned U-Boot `ece349ade2973e220f524ce59e59711cc919263f`,
`board/sunxi/board.c:537`, returns device0 for BOOT_DEVICE_MMC1 (SD), and device1
for BOOT_DEVICE_MMC2. The configured environment index is only its default case.
`env/mmc.c:465` calls that function for redundant environment loading.
The existing wrapper trusts in-memory environment variables before loading its
marker/FIT. Reading the signed target's actual environment is therefore necessary
for the SD-to-eMMC route. Individual failing in-memory predicates were not printed.

The actual retained loader configuration enables CMD_MMC, CMD_IMPORTENV and
ENV_REDUNDANT, with 64KiB records at4MiB/8MiB. Pinned `cmd/nvedit.c:767`
implements `env import -c ADDRESS SIZE [VARIABLES...]`: CRC checking uses the
compiled `env_t` data offset, including its redundancy flag. A variable list
limits imported names; `-r` means CRLF handling, not redundant-header selection.
Primary source hashes and excerpts are privately retained beside the physical
receipts. Accessed2026-10-01. No upstream source or loader has been changed.

## Bounded correction

Use supported U-Boot MMC reads and CRC-checked, whitelisted environment import
in the generated selector. Read both64KiB copies from the intended eMMC user
area and require each to contain the exact job token, layout, exhausted counters
and BOOT_ORDER=A B. Reset the five gate variables before each import so absent
fields cannot inherit defaults or the other record. Preserve routing variables
and unrelated RAM environment data. Both copies must pass before marker/FIT
admission; no arbitrary environment text may execute.

Keep source/target routing explicit and bound to the existing approved profile;
reject an unknown or changed route rather than infer device identity. Do not
change persistent environment data, bootloader/SPL, kernel, signed-job purpose,
claim protocol, raw writer, live target admission or marker-last behavior. Retain
all original marker/FIT length, CRC, iminfo, purpose/hash and fallback checks.
Both preflight and ordinary handoff composition require the same stronger source
admission; write mode remains independently compiled and signed.

Allocate two64KiB RAM buffers with checked nonoverlap against the existing marker,
FIT, script, kernel/initrd and DTB intervals. Report the128KiB static increment;
it is not physical RAM or relocation qualification. The existing original-script
fallback must remain reachable on every failed read/import/predicate.

## Ownership and validation

One implementer owns exactly:

- `scripts/build_h616_recovery_handoff.py`
- `tests/test_h616_recovery_handoff.py`
- `tests/test_recovery_handoff_stage.py`
- `tests/uboot_recovery_handoff.py`
- `docs/design/unattended-emmc-reimage-handoff.md`
- `docs/hardware/host-h616-physical-preflight.md`

Return any needed additional production ownership before editing. The coordinator
owns this record, proposal, decisions and shared goal/human records.

Use actual pinned U-Boot sandbox environment import with ordinary and redundant
fixtures, including the same compiled redundancy setting. Demonstrate success
when RAM begins with SD defaults but both eMMC copies are correct; prove fallback
for either invalid CRC/read, missing field, wrong token/layout/order/counter,
changed route and marker/FIT failure. Distinguish any fixture transport substitution
from actual MMC reads. Inspect the complete generated script for absence of
saveenv, mmc write/erase, target writes and guard bypasses. Check that unrelated
routing values survive and absent gate variables cannot be inherited.

Run relevant composition/staging/purpose-binding regressions and representative
nondeployable composition only with retained pinned inputs. No source download,
installer, full-image/QEMU repeat, real signing job/key or hardware operation.
Scratch<=512MiB in assigned tmpfs; additional retained artifacts<=64MiB only when
persistent storage admission passes. Root storage is tight; never copy old/new
artifacts for review. Independent delivery verification must use a separate
session from author, planner, approver and evidence producer.

## Human and hardware dependency

[H12](../../hardware/coordinated-human-tasks.md) remains the canonical physical
queue. Offline approval grants no new hardware authority. The owner has standing
urh-04 authority, but SD return/recovery, replacement expired inputs, fresh target
admission and every later consequential operation require their own exact review
and observed checks. Do not reuse this failed attempt's job or claim, remove its
marker, retry its boot or claim urh-04/05 acceptance through offline tests.
