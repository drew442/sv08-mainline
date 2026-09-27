# H616 commissioning policy: audited v5 image map

This offline change pins the exact raw image identity found in the [v5 GPT
audit](host-board-image-20260925-v5-gpt-audit-20260927.md) into the H616
commissioning policy builder. It binds raw SHA-256
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f` to image
disk GUID `b643a41a-d63f-40aa-9940-74a8f4e19a8d` and all six ordered GPT
records. The builder also checks those records against the current layout and
SV08 board profile, failing closed if either changes.

Validation ran offline on 2026-09-27. The focused builder and host layout
suite passed 25 tests, including exact audit comparison and refusal of changed
image hash, disk GUID, PARTUUID, offset, size and partition order. Existing
synthetic behavior and the default read-only diagnostic separation checks
passed. The candidate's generated manifest is SHA-256
`715cbcefc408f96eb0b532207308fd50a7d792e777d51e655ed24547e28aae10`; its
binary is SHA-256
`a5f5c226f50e06139f61cbb13f5dbfebe6bb6d0c7549955ce929c9db8b0090ca`.
Both private outputs remain under
`local/integration-evidence/network-emmc-v5-image-map/candidate/`.

The generated artifact is a compile-time policy fixture, not a usable image:
it was signed with repository synthetic test keys and placeholder local target
identity, contains no bootable SD image or trigger, reports
`nondeployable-commissioning-candidate`, and sets
`physical_target_validated: false`. No printer or eMMC was accessed. The image
hash and GPT map are historical artifact evidence, not a current eMMC reading.
This change does not approve a physical build, write, boot-policy operation,
H12 commissioning, claim trust or release. The private v5 eMMC image was not
needed or copied to this VM.

Exact source hashes used for the checks:

| Input | SHA-256 |
| --- | --- |
| `scripts/build_h616_reimage_candidate.py` | `2203a052bcc987825703c4513a369b8e6bc70133cb6a42c9b3ff38af691aa420` |
| `tests/test_h616_reimage_candidate.py` | `4f92eee8bab994471378f82e891b89dbbaf01f5278f8e3c4cabda7890c6d7400` |
| `configs/host-os/recovery-test-sv08-01.json` | `1047d7cd5c2d823aae4b6f5bd590d289d9fc0465a0b056533fdc49bfd3926751` |
| `docs/hardware/host-board-image-20260925-v5-gpt-audit-20260927.json` | `eb1b5fbe55a31b75dbc874fd7425428050951400c928567034e40a79be6b949c` |
| generated `reimage-manifest.json` (private test fixture) | `715cbcefc408f96eb0b532207308fd50a7d792e777d51e655ed24547e28aae10` |

The independently reviewed implementation commit and verifier evidence are
recorded in the feature workflow record after review.
