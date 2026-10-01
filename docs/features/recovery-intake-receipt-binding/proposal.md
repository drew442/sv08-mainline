# recovery-intake-receipt-binding: accurate intake completion receipt

Kind: fix. Author: root/coordinator. Date: 2026-10-01.

## Problem and evidence

At dfc3c54, scripts/recovery_image.py intake parses lock.read_text(), verifies
archives from that parsed lock, then hashes the pathname again for its successful
receipt. A replacement between parsing and receipt can falsely name another lock.
This source-derived race remains an explicit required G4 item in the host checklist
and the historical recovery image evidence. No physical failure is asserted.

## Intended outcome

Parse and hash one captured byte buffer. After downloads verify, compare current
lock content against that digest and refuse changed or unreadable content. Return
the captured digest, without a later path rehash. Demonstrate baseline false success
and candidate refusal deterministically with tiny synthetic archives and mocked
network response; unchanged content yields the accurate successful receipt.

## Scope and alternatives

Only intake content reporting, focused tests and evidence documentation change.
Receipt shape, unprivileged/fresh output, path constraints, download verification,
retry and independently revalidated assembly gates remain intact. Same-byte
replacement may pass; content identity is checked at the completion validation
point, without claiming perpetual pathname stability or detecting A-to-B-to-A.
Advisory locking would not exclude uncooperative writers and adds unnecessary
coordination. No change leaves a required defect. Standard library byte hashing
suffices; no upstream pin, dependency, image geometry, preservation, boot policy,
printer behavior or hardware authority changes. Custom builder retirement remains
ADR 0014's supported upstream image builder path. Prior accepted recovery evidence
retains its original revision; changed builder freshness gates must never be waived.

## Acceptance and task split

One offline intake-binding task, owned scripts/recovery_image.py,
tests/test_recovery_image.py and its dated development evidence document.
Check receipt-continuity: actual intake unchanged/replaced/deleted lock cases,
same-byte replacement and a replacement after completion comparison (receipt must
still name captured bytes), baseline/candidate comparison, no completion success
on refusal. Check preserved-gates: inspection creates no outputs/network calls;
existing fresh-output/path/symlink/refusal, download hash/size failures and relevant
assembly completion input gates pass. Use isolated tiny fixtures and no real
network, privileged operation, recovery rebuild or QEMU/physical image.
Fresh independent delivery verifier reviews actual committed source/evidence and
full diff. Offline receipt correctness does not prove assembled image or hardware.

## Human dependencies

None for this offline fix. Existing H12 physical reset and H04/H07 recovery/media
acceptance remain in coordinated-human-tasks.md; this grants no hardware operation.
