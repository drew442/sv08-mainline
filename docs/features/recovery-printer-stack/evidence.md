# Complete-stack recovery qualification: blocked candidate

This candidate is **not end-to-end qualified**. It preserves tested recovery compatibility fixes and a disposable full installed-stack harness. The goal remains incomplete; the review PR is draft, with no merge or deployment claim.

## Changes and demonstrated outcomes

Normal identity `current`/`previous` selectors and systemd’s log README previously prevented backup/activation. Archive v2 preserves these narrowly allowlisted literal links without following them, with checksummed metadata, deferred safe extraction, ownership and v1 read compatibility. Arbitrary, escaping, cyclic, missing-generation, special and unsafe objects remain refused. Normal/recovery staging includes the matching reader.

Actual installed full-stack boot exposed a Cockpit socket ordering cycle. Its staged drop-in removes default socket ordering while explicitly retaining sysinit admission, Identity failure/order dependencies and shutdown cleanup. The actual boot log reported the socket job deleted to break the cycle. Focused fresh/refresh staging checks pass; a new normal boot after this fix is still required.

The fixture now canonicalizes its factory draft before saving/generating, preventing JSON field ordering from making strict generated-byte expectations differ. The original failed expectations remain preserved. Production generation, parser resource limits, calibration/printing guards, authentication and TLS verification were not relaxed.

## Evidence and blocker

Source-bound receipts and file hashes are in [evidence.json](evidence.json). Private originals remain under `/home/drew/.sv08-recovery-stack-20261013` and `/root/.sv08-recovery-stack-20261013/fixture`; generated disks, private synthetic keys/passwords and full service logs are not published.

- Original archive/export/restore/activation/builder/staging root suite: 122 passed, no skips; applicable unchanged compatibility evidence reused.
- Boot/identity/network/web/printer regressions: 128 checks, 126 passed and two environment-dependent host parser checks skipped.
- Current canonical harness: 12 passed; current recovery image/staging contracts: 25 passed; existing administrator staging: 20 passed. These are offline checks, not browser or hardware acceptance.
- Current normal and recovery image builds passed, bound to the corrected guest/staging source.
- Earlier full-system preparation passed, but is explicitly preparation-only and used an older guest revision. An earlier normal boot preserved actual configuration bytes and reached real service startup after manually starting Cockpit; it failed strict regenerated-bundle comparison. It is not a qualification pass.
- Fresh canonical preparation using aligned instruction-count time failed the unchanged validator with SIGKILL/no diagnostic. The cause of that latest kill is not established. A changed run using the previously successful unaligned clock failed the unchanged ten-second readiness deadline. Both failures and partial state are retained; their QEMU process exit zero after clean poweroff is **not** acceptance success.

The installed production validator retains its pinned dictionary/entry hashes, 256MiB address-space limit, eight CPU seconds and ten-second readiness deadline. No demonstrated disposable invocation now provides a reproducible pass. Further unchanged reruns or clock speculation would not close this gap. Next useful action is native ARM64 execution within explicitly approved disposable authority, or a concrete QEMU accounting diagnosis. No printer access is authorized by this candidate.

The full source-backup → installed recovery restore → reviewed activation → two distinct normal boots → previous-stack rollback sequence and real browser/strict TLS/authentication persistence remain unqualified. There is no representative restored-stack screenshot because that journey did not pass.

## Boundaries and preservation

Generic Cortex-A53 QEMU and reused generic 6.12 kernel do not qualify the H616 kernel, CPU budget, factory image fit, physical rescue SD, power cuts, MCU communication or printing. Synthetic paired-OS PAM authentication is distinct from restored Moonraker/gateway/SSH identity; no portable Linux-password restoration claim is made. Archive v2 requires this matching recovery reader; the existing physical rescue SD was not updated.

Historical cached root receipt mismatch was preserved. The derived observed input was package-verified; matching cached RAUC and missing generic kernel module payload were staged only into owned disposable roots. Historical inputs/evidence were not rewritten. Failed/retired images remain accounted for, and all guests were cleanly stopped before media reuse. The initial 10,800 process-second allowance remains, with recorded cumulative output continuations to 48GiB and 26GiB free at the latest storage check.

Named task-scoped workers were used with fresh context: researcher at omitted effort, implementer at requested medium, pinned supplemental source verifier, and fresh integration at omitted effort. Effective runtime model/effort was not independently measured in this delivery. No performance, token-saving, independent release approval or physical-hardware claim is made.
