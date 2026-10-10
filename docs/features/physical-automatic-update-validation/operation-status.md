# Physical update qualification operation

The owner authorized the healthy and deliberately unhealthy automatic update goal, with inactive outputs and preserved data. On 2026-10-10 they confirmed the previously tested rescue SD remains available. Availability is owner-reported; prior independent recovery boot/SSH evidence is documented in the coordinated hardware record.

The exact [operation packet](operation-packet.json) binds preparation source b431902, signed bundle/index hashes, actual printer identity/geometry, write boundaries, inactive outputs, account preservation, stop conditions and physical acceptance. [Independent high-effort assessment](operation-review.md) passed with conditions; [structured review](operation-review.json) preserves exact bindings and distinctions between reported, measured and inferred evidence. The fixed configured Sol/high profile was verified; actual sampling telemetry is unavailable.

The source preparation task is complete. Physical H13 execution is in progress; no physical success or printing release is claimed by this preparation record. Final measurements and preservation comparisons will supersede this status after actual completion.

The first bootstrap stopped before RAUC/feed activation: kernel masks take systemd precedence and report `masked-runtime` even when persistent `/etc` masks exist. The stopped printer remained reachable, read-only, outputs inactive, automatic policy disabled and pending state empty; complete preservation comparisons passed. The restart guard now independently checks exact persistent masks when runtime masks take precedence, with 30 relevant tests passing. No volatile-only exception was added.

The separately reviewed [continuation packet](continuation-operation-packet.json) permits one exact source runtime repair and controlled source-A warm boot, then the corrected signed update pair. [Continuation assessment](continuation-review.md) passed with conditions; its [structured record](continuation-review.json) retains exact new hashes and the source-readiness boundary. The original stopped attempt remains evidence and is not represented as success.
