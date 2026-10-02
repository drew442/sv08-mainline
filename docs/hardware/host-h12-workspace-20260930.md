# H12 volatile workspace capacity, 2026-09-30

**Historical H12 record:** The [2026-10-02 owner-selected scope](../decisions/20261002-h12-scope-reduction.md)
supersedes this document’s earlier RAM, signed-permission, separate-preflight,
automatic-return and cold-capture plans. Preserve the measurements below; use
the current attended SD procedure for future work.

The coordinator enlarged the running SD recovery host's existing `/tmp` tmpfs
limit from 64 MiB to 256 MiB after a separate exact-operation high-consequence
review. This completes one reversible H12 preparation step. It stages no artifact
and establishes no physical preflight, reimage or printer result.

## Reason and boundary

The previously measured representative artifact occupies 97,796,907 bytes across
its required members; staging verification temporarily extracts another
48,897,855 bytes. The fresh host had 83,165,184 bytes free in `/run`, about64MiB
in `/tmp` and32MiB in `/dev/shm`. No single existing volatile mount could hold the
complete artifact. Final physical v2 artifact sizes, runtime memory and staging
space still require their own admission checks.

Only `/tmp`'s capacity limit changed. Linux6.18.51 `mm/shmem.c:4841-4912`
validates reconfiguration and updates `max_blocks`; this is a filesystem ceiling,
not a memory reservation. Source: retained pinned kernel at
`build/host-kernel-61851-v1/linux-6.18.51/mm/shmem.c`, inspected2026-09-30.
No persistent configuration, service, source export, target/environment,
UART, boot, MCU, heater or motion operation was included.

## Review and execution

The initial medium review failed because the proposed rollback could remount
an uncertain `/tmp` target. That script and verdict remain preserved. The revised
script has exactly one mutation and no automatic rollback, retry or reboot.
Any command/observation failure stops for read-only state reconciliation.

The named native review launch hit the runtime thread limit. The coordinator used
the documented separate-session fallback with the full exact
`high_consequence_reviewer_high` contract, GPT-6.1 Sol/high. Actual model, effort,
full-access/approval-never execution and exact developer contract were independently
observed for session `01a0f271-8d49-7c73-87f8-0f68193047b2`. Its verdict was
**PASS WITH CONDITIONS**. The reviewer did not perform the operation.

The coordinator satisfied the conditions after the
[node-binding repair](host-h616-emmc-node-binding.md) passed independent delivery
verification and its task was completed. Strict enrolled SSH checking, a clean
`sudo env -i` interpreter invocation with isolated imports and disabled bytecode,
fresh same-boot/root/tmpfs/mode/usage/memory checks and exclusive coordinator
operation preceded the change. The reviewed script's SHA-256 is
`9f65a9293bb22096ce600a0e807b5b88a71db7bba4780bcbab87d2435849d6bf`.
Both SSH/script exit were zero with parsed `PASS`; a separate read-only postcheck
verified the result.

## Measured result

Target: authenticated recovery host at the reserved printer address, boot ID
`baad0a1d-d3dd-4691-a7c0-c8a79b7343c6`. Host board revision
`H616_JC_6Z_V1.2` remains owner-reported. This operation adds no board-identity proof.

| Observation | Result |
| --- | --- |
| SD root | `/dev/mmcblk1p2`,179:2,ext4; superblock options `ro,norecovery` unchanged |
| `/tmp` identity/options | tmpfs,0:24,`rw,nosuid,nodev,relatime`, unchanged |
| `/tmp` limit/free/used | 268,435,456 /268,431,360 /4096 bytes |
| `/tmp` mode/statvfs flags | 1777 /4102, unchanged |
| Other selected mounts | `/run` and `/dev/shm` identities/options unchanged |
| Postcheck available memory/swap | 848,601,088 bytes /0 |
| Artifact allocation/staging | None |

Ignored coordinator evidence under
`local/feature-workflow/probes/h616-physical-preflight/h12-access-20260930/`
retains both review candidates/verdicts, actual runtime observations, exact
invocation and hashes, fresh before/after measurements, stdout/stderr/exit and
`workspace-review-v2/postcheck.json`. No credentials or private hardware dump
is committed.

The limit is volatile and will be lost on reboot. A later shrink requires verified
same-mount identity and usage fitting the lower limit; none is performed here.
Fresh jobs/keys, reviewed physical artifacts, capture readiness and separately
reviewed staging, arming and boot remain pending under the
[H12 task](coordinated-human-tasks.md). Full write/readback follows physical
preflight; neither follows automatically from this workspace result.
