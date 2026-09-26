# network-emmc-cid-admission: Bind a writer target to a pinned eMMC identity

Kind: improvement. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The reusable locator in `tests/fixtures/sd-network-root/emmc_locator.h` selects
one MMC by controller, type and exact capacity. Its contract explicitly does not
establish a unique card identity. H10 measured 61,079,552 sectors below H616
controller `4022000.mmc`, but did not record a CID; see
[`host-network-emmc-target-admission.md`](../../hardware/host-network-emmc-target-admission.md).
The readiness audit says the v5 A-rearm record contains a private prior CID, but
the live card has not been matched to it. The QEMU writer and one-shot protocol
use synthetic USB `/dev/sda`, not the printer eMMC, and explicitly exclude live
CID admission. These are distinct measured and synthetic facts.

## Intended outcome

Add a small writer-side identity-admission function that accepts the already
reviewed controller/type/capacity candidate plus an expected CID supplied from a
locally trusted target-specific configuration. It reads the candidate's live
sysfs CID and returns an admitted target only when exactly one candidate matches
all fields. Missing, malformed, changed, mismatched or ambiguous identity must
refuse before the writer opens any block node. Synthetic fixture CIDs prove the
comparison and prove that rejection precedes target open. The network job
 descriptor cannot supply or override the expected CID.

This creates a testable prerequisite for a future installed-eMMC writer adapter.
It does not create that adapter, choose a production expected-CID store, include
writer code in the SD/NFS image, or authorize a physical write. H12 remains the
single later physical commissioning session.

## Scope and alternatives

Included: an isolated identity-admission helper under test-only writer sources,
synthetic sysfs and target-open spy tests, and documentation of the unresolved
expected-CID provisioning boundary. Preserve the current read-only diagnostic
locator and its output. Keep expected CIDs private; check in only obviously
synthetic values. Keep the production SD/NFS image and boot policy unchanged.

Excluded: reading private `local/` or `backups/` data, adding a real CID to Git,
provisioning a target identity, making a production service/image, opening a real
block device, any hardware access, reboot, or physical write. An alternative is
to rely on type/capacity and operator confirmation; that fails the unattended
identity requirement. Broader writer integration is deferred until an
independently reviewed target-identity source and exact writer are ready. If a
safe local expected-CID source cannot be established offline, document the
boundary and stop before wiring the helper into any write path.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `nca-01` | `cid-admission` | Synthetic sysfs inventory admits only an exact expected/live CID match combined with the existing controller/type/capacity rules; absent, malformed, mismatch, or multiple candidates refuse. |
| `nca-02` | `cid-admission` | Tests prove every refusal occurs before any block-node open; job/network input cannot override expected CID. |
| `nca-03` | `cid-admission` | The existing read-only probe and production SD/NFS builder remain behaviorally unchanged and contain no writer or CID secret. |
| `nca-04` | `cid-admission` | Focused native and static ARM64 `-Werror` tests, existing locator/SD-NFS tests, workflow and docs/hash checks pass; report states that synthetic IDs do not validate printer identity. |

All checks are offline and synthetic. No hardware write or boot-policy change is
included.

## Human dependencies

No human work is needed for this offline task. Reuse H12 in
[`coordinated-human-tasks.md`](../../hardware/coordinated-human-tasks.md) for
one future live CID comparison within the existing supervised commissioning;
do not add another physical task. Keep the factory eMMC stored. Feature approval
does not authorize that physical action. The expected-CID provisioning method is
a design boundary for later exact review, not a request for the owner to disclose
the private CID in chat or Git.
