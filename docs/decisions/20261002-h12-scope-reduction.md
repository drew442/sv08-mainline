# H12 scope reduction at the owner’s direction

Date: 2026-10-02. Authority: explicit owner decision in the project conversation.

## Decision effective immediately

The owner stated: “we do not need to prevent someone from forging or replaying
permission to reimage the host, completely and strictly abandon work on this.”

Abandon the H12 anti-forgery/anti-replay permission mechanism as a requirement
and workstream: guest random challenges, secure entropy acquisition for those
challenges, authenticated claim receipts, claim signing/verification, server-side
permission replay prevention, and permission expiry/clock enforcement solely
serving that mechanism. Do not develop, test, physically trial, provision or
repair this mechanism, or make its success a prerequisite for further H12 work.
Do not substitute a different permission protocol or randomness workaround.
This owner decision supersedes conflicting historical feature constraints.

Completed code, reviews and evidence remain historical facts. The mechanism is
still present in existing source/artifacts; this record does not claim its code
has been removed or deployed behavior changed. The planned physical entropy
trial and further signed-permission job preparation are withdrawn. Removing the
obsolete dependencies belongs to the simplified route selected next, without
new development or validation of the abandoned mechanism itself.

Accidental repeated flashing after reboot is a separate engineering concern
from malicious permission replay; the remaining minimal trigger/stop behavior
uses the owner-selected attended yes/no confirmation described below. Source checksums, exact target
identity and readback also have independent corruption/wrong-device purposes.
This decision does not alter ordinary SSH access or unrelated OS-update signing.
No printer operation or image write is authorized by this document itself.

## Owner-selected scope

The owner subsequently chose the following scope explicitly. This supersedes
both the earlier recommendations and conflicting historical H12 gates.

| Point | Owner decision | Active interpretation |
| --- | --- | --- |
| 1. Reimage installed eMMC | Keep | Preserve complete-image replacement without removing eMMC. |
| 2. Maintenance environment | Abandon RAM maintenance; SD is sufficient | Run the maintenance OS from independent SD. No RAM handoff, RAM-writer boot or associated FIT relocation work is required. Ordinary RAM use by the SD OS is unaffected. |
| 3. Automatic launch | Defer until further notice | Do not develop the running-system-to-maintenance automatic reboot/staging route or make it a completion prerequisite. |
| 4. Separate rehearsal | Explanation requested; no decision yet | Present an optional nonwriting check of the selected SD route. Do not retain the old RAM preflight as an implicit gate. |
| 5. Automatic recovery return | Defer until further notice | Manual restart/SD recovery is acceptable; no automatic return requirement for H12 completion. |
| 6. Target/image checks | Keep, minimum viable and simple | Identify intended eMMC, sufficient capacity, source independence and image checksum with the smallest practical implementation. |
| 7. Write/readback verification | Keep, minimum viable and simple | Flush and compare the written image bytes with the source, with a clear result. |
| 8. Repeat-flashing behavior | An attended yes/no prompt is sufficient | Require an affirmative answer before each write. No answer/No performs no write. If reboot returns to the prompt repeatedly, the operator handles it; automatic loop detection or server-side single-use permission is not required. Automatic reboot initiation remains deferred under point 3. |
| 9. Recovery | SD recovery is sufficient | Do not require factory-eMMC fallback as an additional H12 acceptance gate. Its stored physical position remains unchanged. |
| 10. Complete initial boot capture | Abandon | No further cold-capture research, implementation, trial or completeness gate. Existing ordinary logs can be used without new capture development. |

## Point 4 explanation for the owner

For the selected SD route, a rehearsal would start the maintenance tool in a
nonwriting mode, locate the proposed image and target, and show the target,
image size/checksum and whether eMMC is unused by the running system. It would
then stop. Its purpose is to catch a wrong path, unavailable image or mounted
target before a destructive transfer. It would not test a RAM boot, permission
server, secure randomness or automatic return.

An alternative is to perform those same minimum checks immediately before the
normal yes/no prompt, without a separate rehearsal feature or milestone. The
coordinator recommends this integrated approach for the owner’s minimum viable
scope. The owner has requested an explanation, not yet selected point 4.

## Execution consequences

The old stage/arm/activate/RAM-preflight/automatic-return sequence is withdrawn
from the live plan. Existing code, images, installed old boot settings and
historical results are retained as evidence, not represented as removed or
adapted already. Define the smallest SD-based implementation from this scope;
remove obsolete permission/RAM dependencies from that path rather than repairing
or physically trialing them. No active child agent is assigned the abandoned work.

The selected scope is not itself a request to perform an immediate full-image
write or another physical restart. Continue authorized offline preparation under
this scope; any actual write still identifies its target/image/recovery path and
uses the existing independent hardware review. Do not ask the owner to approve
these scope decisions again.
