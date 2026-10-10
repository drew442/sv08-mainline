# H616 offload comparison evidence — 2026-10-10

## Outcome

Bounded installed CE execution and source/model analysis are complete. Three supported
request sizes have matching hardware/task counts, zero fallback and correct digests.
Larger one-shot/streaming attempts fall back. Python/OpenSSL and dm-verity inspected
consumers do not use this CE AHASH path. The end-to-end timings are serial planning
scenarios; there was no actual update or independent CPU software benchmark.

See [results and timing explanation](../../hardware/host-crypto-offload.md) and
[sanitized JSON](results.json). No update policy product controls were changed.

## Actual checks and provenance

The coordinator streamed the exact script as safely shell-quoted `python3 -c` through
the established trusted SSH connection and passed expected synthetic zero-message
SHA-256 digests on stdin. Existing sudo authentication was used; no credentials or
private identity data are published. There were no guest script/data files, installations,
images, filesystem changes, module reloads, service starts, updates or reboot requests.

Workstation correctness-input generation:

```python
sizes = [4096, 16384, 28672, 32768, 65536, 8 * 1024 * 1024]
expected = {str(n): hashlib.sha256(bytes(n)).hexdigest() for n in sizes}
```

On the installed system the script reads that JSON from stdin, binds the explicit
SHA CE algorithm and outputs JSON. A direct invocation, when the owner places the
script/input in an approved temporary location, is:

```sh
sudo -n env PYTHONDONTWRITEBYTECODE=1 python3 host_crypto_offload.py < expected-digests.json
```

The actual streamed invocation returned exit 0, empty stderr, status passed; every
accepted digest, every expected hardware/fallback counter delta, same boot/service/mask
state, root/boot read-only and the byte/time limits were inspected. AST parsing and
`git diff --check` passed. An offline arithmetic/lineage check rehashed the script and
all private receipts, reconstructed the two earlier script versions to their execution
hashes, and verified processed bytes, modeled components and digest-reference mappings.

Final script SHA-256: `b6f139aaaf47e982771e57814897ebea4d11b649a490b32d6a01742452efa2fa`.
Sanitized result SHA-256: `6f2e551b31895e9e8834c0c7be0696ede176cde9e04a60ca9adec9a68a6a4215`.
Raw final JSON receipt SHA-256: `9b9882d926411e693e913fec6b52caf3bd2bdfd1fa072155e4e0c1d5f81014a3`.
Remote invocation receipt SHA-256: `291260f3845e231d36df0b5c1869e7452b61947ef2869684bb5ee10aa6bd1cdb`.
Private receipt hashes for the preliminary/failed invocations and preflight snapshots
are retained in results.json; no failed attempt was relabelled passed.

## Scope and preservation

Named system: test-sv08-01 diagnostic candidate, H616, physical board revision unknown.
Kernel 6.18.51-sv08-candidate1; kernel hash/AF_ALG/dm-verity source analysis matched the
pinned 6.18.51 candidate source. Measurements are synthetic cache-warm requests, not
an installed application update or a raw hardware bandwidth test. Loop overhead/digest
comparison is included. Process CPU utilization excludes kernel threads/interrupts.

The measured final invocation processed 461,434,880 bytes; the lineage processed
532,713,472 bytes over 13.832 seconds of measured remote command duration, with no
more than 64 KiB reusable synthetic benchmark memory. The 180-second process,
1 GiB processed and 16 MiB generated-artifact allowances were not exhausted.
No historic images or disposable systems were created/copied/deleted. Local retained
public sources and logs are small; no remote image-storage reservation was needed.

Root/boot read-only, unchanged boot ID and inactive inspected services/masks were
checked before and after. No entire-data preservation hash or printer qualification
is claimed; authentication logs can change normally. Heating/motion/printing services
were not enabled. No network/storage/decompression/reboot stage was benchmarked.

## Agents and validation route

Two research agents traced update stages and kernel CE/AF_ALG/dm-verity semantics;
only the coordinator contacted the printer. Their requested project_researcher profile
uses Sol/low, but effective runtime model/effort was not observable. Workers performed
no hardware measurements, tracked edits, commits or child launches. The coordinator
self-validated source, execution receipts and arithmetic. Source research assessment
is not a fabricated independent delivery verification; this feature uses the self route.

## Limitations and next decision

The diagnostic installed feed module is absent and its other updater files differ from
current repository inputs. End-to-end assumptions describe the repository flow and
representative reliability bundle, not a deployed automatic updater. Current feed waits
for the next reboot; immediate reboot is an explicit finite-model assumption. CPU SHA,
flash, decompression and boot times are deliberately unmeasured. Neither hardware
capability nor AF_ALG throughput establishes an application speedup. Keep the current
CPU-instruction path unless a future suitable streaming integration has evidence of a
useful benefit. Update-policy/recovery integration remain separate owner goals.
