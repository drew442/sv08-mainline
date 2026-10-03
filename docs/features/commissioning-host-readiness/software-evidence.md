# Software delivery evidence

Date: 2026-10-03. Candidate for independent high-effort full-diff review.
Author/runtime and bounded execution are recorded in [execution](execution.md),
[the software contract](software-contract.md), and the sanitized
[receipt](software-evidence.json). No installed completion is claimed here.

## Results

- Fifteen focused tests pass; the optional selected-tool test is separately
  evidenced with 18 actual selected ARM64 libubootenv regular-file cases under
  QEMU. Tests cover selection/wrap/CRCs, single write/no-op, other values and
  bytes outside both regions, real competing locks and killed processes.
- 112 affected regression/integration/UI tests pass. Default staging includes an
  inert module, without its service, private configuration or enablement.
- Ordinary tests build fixtures from immutable Git history and synthetic branding;
  collection and execution need no ignored workstation files. Selected ARM64
  tooling requires explicit opt-in and a supplied root; it is never downloaded.
- Existing/current host-page and actual packaged Cockpit 337 static login assets
  render in Chromium at 1440x900 and 1024x600. Focus, errors, disabled controls and
  confirmations remain visible. Login normal-text contrast is at least 4.5:1.
  Synthetic authentication responses do not establish installed login/elevation.
- Exact historical runtime closure, accepted TLS delta, committed-HEAD-independent
  CSS staging, separate physical capacity/GPT footprint, and file modes are
  checked. State stays executable0755 through the existing sv08-state symlink;
  boot stays0644. Isolated unit-graph validation passes.

## Coordinator checks and corrections

Read-only installed inspection matched all23 historical runtime sources and the
selected tool/library contents. The exact private overlay has12 files,75,774bytes,
18 module dependencies and39,024known preimage bytes. The measured target has ample
space/inodes. Actual preflight passes without writing or changing services.

The first actual preflight refused the stager's incorrect0644 assumption for the
existing executable state command. The author corrected both preimage and payload
modes and tested direct execution through its unchanged command symlink. The
original refusal is preserved. Earlier corrections and failed fixture attempts
remain recorded; none are reclassified as passing evidence.

Coordinator visual diagnosis found that a synthetic HTTP Basic challenge suspended
the headless fixture before the form appeared. Removing that fixture challenge
exposed genuine PF6 selector/contrast issues, then the author fixed and reran the
selected packaged login assets. This says nothing about installed authentication.

The owner-selected password method is the separate
[access amendment](owner-access-amendment.md); it changes the operational actor,
not these software checks. Hardware installation, first confirmation, two restarts,
real authenticated administration and both live MCU identities remain the installed
task, with exact-operation review and physical facts. H12 stays complete.

Raw logs, screenshots, original artifacts and per-turn source hashes remain in
ignored coordinator scratch; the JSON receipt binds their digests. No generated
screenshots, device dumps, private bindings or credentials are committed.
