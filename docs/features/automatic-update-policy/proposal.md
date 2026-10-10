# Automatic update policy and activation

Implement strict automatic provenance, reviewed per-update manual exceptions and individually configurable admission checks. Retain immutable physical safety checks. Track automatic reboot dispatch durably and reuse idle/shutdown admission so uncertain dispatch is not replayed. Existing boot health confirms or falls back.

Acceptance: strict/default and individual-exception policy matrix; digest/revision-bound upload and staging; real patched RAUC unknown-signer admission only manually with damaged signatures/payload refused; automatic trusted discovery through one controlled reboot and health or fallback in disposable ARM; opt-out/busy/policy/reboot uncertainty checks; public receipts and bounded storage cleanup. Authorization is the adjacent owner-request.md. A targeted independent review covers trust-chain-only bypass and reboot crash/concurrency semantics. No physical installation or printing release claim.
