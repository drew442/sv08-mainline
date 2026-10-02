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
is presented for the owner’s decision below. Source checksums, exact target
identity and readback also have independent corruption/wrong-device purposes.
This decision does not alter ordinary SSH access or unrelated OS-update signing.
No printer operation or image write is authorized by this document itself.

## Remaining choices presented to the owner

| Component | Purpose and current position | Coordinator recommendation, not owner decision |
| --- | --- | --- |
| Remote whole-eMMC replacement | Replace the complete system without removing eMMC; alternative is an external reader or a simpler SD-based maintenance session. Offline transfer passed; physical full transfer pending. | Decide whether this capability is needed before first print; defer if manual installation is acceptable. |
| RAM maintenance environment | Keep the running system independent of storage being overwritten. Entered RAM physically. | Keep if retaining remote whole-device replacement; a proven independent SD system is another route. |
| Automatic launch through installed eMMC recovery | Stage a payload on recovery, change redundant boot settings and boot it automatically. Physical entry demonstrated; repeated staging/recovery complexity remains. | Defer automation and consider an attended SD launch. |
| Separate preflight without full-image transfer | Exercise the selected RAM/target path before destructive transfer; current rehearsal has not passed end to end. | Keep a short practical rehearsal of the chosen simpler route. |
| Automatic return to original recovery | Recover without a person intervening. Previous return reached recovery services; display usability and reliability remain incomplete. | Defer if attended restart/SD recovery is acceptable. |
| Wrong-device and image checks | Confirm intended spare, capacity, source separation and complete image checksum. Many checks already implemented. | Keep. |
| Full write flush and readback | Establish that storage contains the intended complete image and layout. Offline passed; physical pending. | Keep. |
| Prevention of accidental repeated writes | Stop a reboot or interrupted run from automatically flashing again. Existing local marker/environment machinery overlaps the more complex launch route. | Keep simple explicit-start/stop behavior; review whether the current machinery is needed. |
| SD rescue and stored factory eMMC | Recover from failed boot or interrupted write. SD SSH currently works; factory module remains stored. | Keep. |
| Complete earliest cold-boot serial capture | Diagnose bytes lost before USB enumeration. | Already abandoned as a prerequisite; use available logs/SSH/warm boot/human observations. |

Until the owner selects the remaining route, do not continue the old H12 physical
sequence just to satisfy superseded permission checks. No live child agent was
working on the abandoned mechanism when this decision was recorded.
