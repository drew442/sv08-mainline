# Commissioning guard repair evidence

## Cause and repair

The PR29 baseline at `d2b37e99e5a1c6c609617fdccf0cb7ab407f8b68` reproduced 18 commissioning tests: 14 passed, three errors and one explicit selected-tool opt-in skip. All three errors correctly refused a bootloader source mismatch. The current bootloader has a default-path environment-device metadata recheck absent from the approved historical composition. The [accepted decision](../../decisions/20261003-commissioning-host-baseline.md) requires exact historical sources and refusal after composition changes.

The test fixture now materializes the accepted pinned bootloader and explicitly staged helper/theme/unit inputs in a disposable source tree, using read-only Git object queries. Production staging, dependency checks, historical pins and runtime code are unchanged. Tests assert exact pinned payload bytes, manifest hash and absent preimage, and refuse both the real current checkout and a locally modified bootloader before creating output. Existing installed preimage, dependency closure, determinism and conflict tests execute successfully.

Pins: BASE `6064628ff06261a604aa13c52e17407b33f9f503`; TLS `8c6f24f5a565cd08e43001414f643f55d5b1bb8b`; dependency `1d1855719169f024b3d36f7e9bbe1fb4d5f28894`. Pinned bootloader SHA256 `b7ab5d71b944259c91ec42152d1557846a131a752c4501bab23f56c4dcd84753`.

## Actual checks

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p 'test_commissioning_host.py' -v` | 19 tests: 18 passed, one existing opt-in selected-tool skip; 6.973 seconds |
| `python3 -m unittest discover -s tests -p 'test_host_integration.py' -v` | 7 passed |
| `TMPDIR=/home/drew/.sv08-commissioning-20261023/tmp python3 -m unittest discover -s tests -p 'test_host_boot_health.py' -v` | 35 passed with private scratch ancestry |
| `git diff --check` | Passed |

The first authored commissioning run contained an incorrect assertion that a separately staged bootloader appeared in the imported-module closure. It was corrected to assert the actual manifest payload contract; refusal and provenance requirements remain. Both runs are retained. Initial boot-health invocations failed because `/tmp`, then the scratch parent, were writable by other users/groups; the final invocation used owned mode0700 scratch and tmp directories. No runtime ancestry protection was relaxed.

## Source-bound artifacts and limitations

Local sanitized logs and input-hash inventory are retained under `/home/drew/.sv08-commissioning-20261023`; hashes below identify the inspected evidence. Submission binds the final candidate and relevant source hashes through the existing feature record. Historical BASE/TLS/dependency object inputs are separately inventoried in the retained report.

| Artifact | SHA256 |
| --- | --- |
| `intake.json` | `08aca8398a984f4eddc4bdfa76997028c25fff0685683eb182330d69f697e136` |
| `worker/commissioning-repaired.log` | `58903cb1047bd0884622bae9ca9298d7a7278723d1f7396a4f10e896fa1a4e1a` |
| `worker/historical-input-hashes.json` | `d82f0391b5aaea88aebd8ec4ced555c90d60a58c7dbcf19086a293989592a239` |
| `test_host_integration.py.log` | `7c7f84658616980c0fc4706088619050c64016062baf4650f5ad88e39bf03573` |
| `test_host_boot_health-private-ancestry.log` | `77a956df0cf8bd1d799bc44dd48444bdb4e58bfa5dc838247e10c4c1adb85c39` |
| `test_host_boot_health.py.log` | `8454b29347c4c3623b1b41894dfc430577a96d3730a140de6ceea38f16101e48` |
| `test_host_boot_health-private-tmp.log` | `8afe17ad974a3332586591292fee20ade2e503987165f504b0b7b5b169e662cc` |

One named `project_implementer` child (`/root/commissioning_repair`), fresh context, omitted effort override: repository default Sol/low requested. Effective runtime model/effort and thread ID were not exposed by dispatch telemetry; no independent review or measured savings claimed. Coordinator inspected the complete diff and actual logs.

Primary allowance: 1200 cumulative process-seconds /512 MiB generated. Worker test runtime13.685 seconds, coordinator baseline5.782 seconds and adjacent tests under2 seconds; record operations are additional. No image builds or downloads; retained logs under256 KiB, generated temporary-data peak not instrumented.

Offline fixture acceptance only. Historical overlay remains nondeployable and refuses incompatible current sources. The selected-tool ARM64 opt-in test was not run. No printer access, physical write, deployment, image rebuilding, installed acceptance or recovery-stack qualification. PR29's historical failed-test evidence remains unchanged.
