# H12 volatile staging tools, 2026-09-30

**Historical H12 record:** The [2026-10-02 owner-selected scope](../decisions/20261002-h12-scope-reduction.md)
supersedes this document’s earlier RAM, signed-permission, separate-preflight,
automatic-return and cold-capture plans. Preserve the measurements below; use
the current attended SD procedure for future work.

The coordinator restored the retained ARM64 tool closure on the running SD
recovery host after an independent exact-operation review. This advances H12
preparation; it is not physical writer, boot-policy or release acceptance.
[Authenticated intake](host-h12-authenticated-intake-20260930.md) remains the
measured target record. No real job or key was prepared by this operation.

## Review and admission

Native reviewer spawn and session reuse returned a thread-limit error while the
single node-binding implementation was active. The coordinator recorded the
[agent guide](../../.codex/agent-guide.md)'s separate-session fallback using the
exact `high_consequence_reviewer` developer contract and profile model/effort.
Selected runtime state and turn context independently confirm GPT-6.1 Sol,
medium, full access and approval never; the exact profile developer contract was
observed in the session. The reviewer did not operate hardware or modify tracked
files. Its own report lists model/effort unknown; the coordinator's runtime
observation is separate evidence, not a rewritten reviewer identity.

The reviewer returned PASS WITH CONDITIONS for exact archive/script hashes,
strict member/type/size/hash checks before file writes, a fresh tmpfs destination
and three version-only calls. Before execution, the coordinator rechecked the
same SD boot ID/kernel, read-only SD root/PARTUUID, /run tmpfs/free space, absent
destinations and Python assertions. It used a clean sudo environment and explicit
Python interpreter with the existing authenticated owner SSH connection.

## Measured result

- Archive SHA-256:
  `499f6c636e8b0f7680974916941a4c6ad91e957c9994522432dbb30faf4642d4`.
  It is 5,932,423 compressed bytes; installed regular content is 14,436,493 bytes.
- All 29 exact entries were checked after installation, including 18 AArch64
  ELF files matching retained package-source bytes, regular wrappers/manifest,
  directories and the sole upstream multicall link `bin/fw_setenv -> fw_printenv`.
  Directories/executable files are root-owned 0700; other regular files 0600.
- SSH and script exited zero. `openssl version` reports OpenSSL 3.5.7;
  `ip -Version` reports iproute2 6.15.0; `dumpimage -V` reports U-Boot 2025.01.
  These are version-call compatibility checks only.
- Final root is `/run/stage-tools`. Staging parent removal and exact file hashes
  passed. `/run` remains tmpfs with its original 96 MiB limit; measured available
  bytes after restore are 83,165,184. No global PATH or service was changed.

No `fw_printenv` or `fw_setenv` command was executed. No eMMC/MCU, persistent
filesystem, boot-policy, heater or motion operation occurred; no reboot ran.
Tools vanish on reboot and do not establish supported host-image compatibility.
The retained package binary hashes establish source identity, not a new upstream
package-authenticity audit. Actual H12 staging still waits for independently
verified node-binding delivery and an exact fresh candidate/operation review.

Ignored evidence is under
`local/feature-workflow/probes/h616-physical-preflight/h12-access-20260930/runtime-tools-review/`:
original packet/script/member hashes, independent review/offline validation,
fallback launch/runtime observations, coordinator admission, pre-operation
checks, operation stdout/stderr/exit and final ownership/hash checks. No binary,
private key, raw device dump or local transcript is committed.
