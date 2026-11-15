# Package and release-gate CI

Add deterministic GitHub PR/main-push/manual checks using existing Python fixtures and test suites for package/native build-input provenance and release/source/license/image-inventory gates. Include relevant production, config, lock, patch, test and workflow changes in triggers. No full image builds, live image mounts, external network qualification, physical hosts or release publication. Keep CI read-only with pinned actions and existing hosted-runner tools.

Acceptance: selected relevant package and gate tests execute successfully in actual GitHub CI; existing altered/missing/stale input negative cases are included. Failed tests, missing selections and unexpected skips fail the check. Preserve bounded per-suite logs, source revision and summary as an always-uploaded artifact, including after test failure. Test the runner failure/log behavior and workflow input triggers. Local deterministic checks and final stable diff pass; publish a PR and inspect the final-head hosted result/artifact.

Primary allowance1800 cumulative process-seconds/512MiB local generated data, plus one normal hosted workflow per changed candidate and bounded failure-directed correction; no additional paid infrastructure or new spending. Initial local free46GiB; no images or compiler roots required. Use scratch /home/drew/.sv08-package-ci-20261023 and a feature worktree.
