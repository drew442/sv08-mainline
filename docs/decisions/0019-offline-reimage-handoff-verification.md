# 0019: Offline proof boundary for the recovery reimage handoff

Date: 2026-09-27. Status: prospective delegated amendment for `urh-03` only.

The first `urh-02/03` submission at `69b1473` failed independent verification.
The QEMU guest was started with external kernel and initramfs arguments, so it
did not execute the staged FIT handoff. Interruption retries had not completed,
and the verifier could not resolve Beelink to inspect the named logs. This
failed review remains in the feature record; it is not superseded as evidence.

An independent GPT-6 Sol/medium feature approver approved a bounded *offline
method* clarification on 2026-09-27. Approval output SHA-256:
`4e00e94588b3e59506fe8b3aec42c2adcefcce5003136cda6db5606a54d3f9f5`.
The original approved decision SHA-256 is
`8d882cc52fed522d7dd0ff974f6a2d10a97779b4ddf49d10bd63a243dbd3e18a`.
The original proposal, decision and completed `urh-01` evidence remain
unchanged. This amendment applies prospectively to a resubmission of
`network-emmc-unattended-recovery-handoff:offline-stage-and-qemu`.

For `urh-03`, offline handoff evidence may be composed of (1) U-Boot sandbox
execution of the compiled dispatcher and selector against disposable staged
media, including armed selection and unarmed/corrupted fallback; and (2) QEMU
virt boot of kernel and initramfs **extracted from the exact FIT staged on the
disposable target**, with hash agreement to the reviewed build. QEMU must run
the actual one-shot controller and RAM writer, complete full write, flush,
independent readback and GPT checks, then boot normal A from that resulting
target. Refusal and interrupted retries must show marker consumption and no
automatic target reopen. `urh-02` staging faults must demonstrate normal boot
or original recovery fallback. Results and serial logs must be available for
independent inspection. Record staging-space and boot-memory measurements.

This offline composition does not prove the H616 U-Boot `bootm` transition,
physical eMMC durability, installed target admission, or printer behavior.
The exact board handoff and fallback remain mandatory at `urh-04`, and a
physical full write/readback/normal boot remains `urh-05`. Each physical
boot-policy change or eMMC write still needs exact target/artifact/recovery
evidence and immediate independent high-consequence review. This decision
grants no physical or release authority.

The independent approver expressly required a dated prospective amendment and
a new scope-bound approval before resubmission. This document records that
approval and its conditions without changing the prior task verification.
