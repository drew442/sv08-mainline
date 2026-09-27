# network-emmc-trusted-writer-boot: Build an authenticated commissioning boot path

Kind: feature. Author: root/coordinator. Date: 2026-09-27.

## Problem and evidence

The writerless goal now has an H616 adapter, a one-open-descriptor identity
check, the audited v5 image/GPT map, and a challenge-bound durable one-shot claim.
Their independent evidence is offline and synthetic. The
[H616 builder](../../../scripts/build_h616_reimage_candidate.py) still emits
a nonbootable root (`bootable_sd_image: false`) with no provisioned trigger.

The existing [SD/NFS builder](../../../scripts/build_sd_network_image.py)
verifies the SD-resident kernel, initramfs and device tree. Its initramfs mounts
the read-only NFS root and then runs `init=/sd-network-init` from that network
root. That is acceptable for the harmless diagnostic, but unsafe for the writer:
a peer able to substitute the NFS root could supply a different root init and
bypass the reviewed writer's image, target and claim checks. The current builder
does not pass `sv08.h616_commissioning=1` or `sv08.claim_port=...`, so the H616
writer cannot complete its required boot-time admission either.

The [latest readiness recheck](../../../docs/hardware/host-network-emmc-reimage-readiness-20260926.md)
confirms the raw v5 hash by streaming the retained compressed input on Beelink;
it does not claim a current CID/dev_t match, a live claim server, or a bootable
writer artifact. The printer's last measured H10 data and older boot traces are
not current hardware observations.

## Intended outcome

Before: the default SD image is a safe read-only diagnostic; a separate H616
writer exists only as an inert nonbootable directory and synthetic QEMU fixture.

After: an explicit commissioning build can produce a separately reviewed SD
boot artifact whose trusted, SD-hash-verified initramfs runs the H616 writer
from initramfs content, mounts the NFS export read-only as an image source, and
never executes a writer from NFS. The host-side commissioning controller can
prepare one exact signed image job and one durable claim, serve the source and
claim only when explicitly invoked, and retain terminal results without retry
or rearm. The ordinary diagnostic build remains writer-free and behaviorally
unchanged.

The artifact remains a nonrelease commissioning tool. Its U-Boot binary is not
authenticated by an SoC secure-boot root; the SD card must therefore remain in
owner custody. This work prevents an NFS peer from substituting the writer; it
does not protect against a substituted physical SD card or network denial of
service. NFS supplies image bytes only, and the writer verifies the complete
image hash before opening the eMMC.

## Scope and alternatives

1. Extend the explicit SD commissioning composition path to place the H616
   writer, exact target policy, job and signatures in the SD-resident
   hash-verified initramfs. Keep the NFS export read-only and use it only for the
   exact raw image source. Change the writer to require and verify the read-only
   NFS source mount at the initramfs handoff path. The trusted initramfs must
   execute the embedded writer before any `switch_root` to untrusted NFS content.
2. Add a local host-side commissioning controller around the existing durable
   claim implementation. It must require ignored local key/input files with
   strict ownership and modes, bind the job to the exact reviewed image/map and
   target policy, use short validity, create durable one-shot state before
   accepting claims, and fail closed after any ambiguous state or lost reply.
   Keep private CID and private keys out of tracked artifacts and logs. Do not
   create production/release keys or automatically start the controller.
3. Exercise the composed boot inputs and controller only with synthetic test
   identity and disposable QEMU media. Keep all generated candidate artifacts
   nondeployable and under ignored local paths.

Do not modify the installed printer boot environment, the default diagnostic,
the normal A/B updater, MCU firmware, or release policy. Do not inspect private
CID material during implementation and do not stage the real v5 image in this
VM. H12 remains the only physical commissioning action. It requires a fresh
live CID/dev_t comparison, exact artifact and recovery review, a separate
high-consequence review, and explicit action authorization before any eMMC
write. No code or synthetic test grants that authority.

The alternative is to leave the SD/NFS path diagnostic-only and defer the
writerless physical test. Executing the writer directly from NFS is rejected
because the network root would control the first privileged code that runs.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `twb-01` | `compose-trusted-initramfs` | The default diagnostic remains writer-free. Only explicit commissioning mode embeds the writer and private-policy-derived public inputs in the SD-hash-verified initramfs; NFS never supplies executable writer code. No installed-eMMC boot policy is changed. |
| `twb-02` | `compose-trusted-initramfs` | Initramfs mounts the exact source NFS export read-only, invokes the embedded writer before switching root, and passes bounded commissioning and claim-port arguments. The writer refuses wrong root mode, missing source, altered input bundle or invalid claim before target open. |
| `twb-03` | `one-shot-host-controller` | Strict local provisioning, exact image/map/job binding, short expiry, durable claim-before-sign, terminal outcome and no retry/rearm are implemented and tested with disposable temporary state. The controller is explicit/manual and uses synthetic keys in tests only. |
| `twb-04` | `end-to-end-qemu` | The exact composed command/initramfs inputs and controller pass success, forged/malformed job, target-identity refusal, source/hash failure, claim replay/lost acknowledgement, abrupt termination, flush/readback fault and unchanged default-diagnostic checks. Artifacts and results are hash-bound; evidence is synthetic only. |
| `twb-05` | `end-to-end-qemu` | Strict ARM64 builds, focused tests, workflow/JSON/local-link/diff validation pass. Reports preserve the lack of H616 boot-ROM authentication, live CID/dev_t evidence, physical eMMC write, physical power-loss recovery and release validation. H12 remains the single physical commissioning gate. |

No owner media move or printer interaction is required for these offline tasks.
Reuse H12 once the verified boot composition, live identity inputs, exact source,
claim controller, recovery procedure and immediate high-consequence review are
ready.
