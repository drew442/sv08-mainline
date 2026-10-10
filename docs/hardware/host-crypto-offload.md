# H616 crypto offload and automatic update timing

## Result and decision

The installed H616 Crypto Engine works, but the available Linux hash driver does not
provide a whole-image streaming SHA-256 path. Three supported AF_ALG one-shot request
sizes produced correct digests and exact hardware request counters:

| Independent message | Median decimal MB/s | Observed range MB/s |
| --- | ---: | ---: |
| 4 KiB | 52.76 | 51.94–56.18 |
| 16 KiB | 120.50 | 119.49–121.86 |
| 28 KiB | 142.22 | 140.72–142.60 |

These are **Python AF_ALG CE one-shot throughput** figures, including socket calls,
DMA/interrupt/scheduling costs and digest comparison in the timed loop. Each size had
three approximately 48 MiB batches; the 28 KiB batches contain 50,319,360 bytes each.
They are not isolated engine bandwidth, file hashing or application update timings.

Single 32/64 KiB requests and one 8 MiB message streamed in 64 KiB sends produced
correct digests **through CPU fallback**, with zero SHA CE tasks. Their timing is not
reported as a software baseline or CE throughput. Independent chunk digests cannot be
concatenated to obtain the SHA-256 digest of an image.

The inspected Python/OpenSSL update consumers do not invoke this CE AHASH path, and
Linux dm-verity uses SHASH, not this asynchronous AHASH driver. Thus enabling this
existing driver does not accelerate those consumers according to source inspection.
There was no actual update timing experiment and no measured end-to-end speedup.
Do not integrate this path into automatic updates based on the one-shot throughput.
A future streaming offloader would need correct incremental SHA semantics and actual
consumer integration before an update-speed benefit could be established.

## Installed measurement

The coordinator used existing trusted Ethernet SSH on `test-sv08-01`, kernel
`6.18.51-sv08-candidate1`, Python 3.13.5, OpenSSL 3.5.7 and RAUC 1.15.2. The processor
reports `sha2`; OpenSSL reports `OPENSSL_armcap=0xbd`, and Python's SHA-256 constructor
is from `_hashlib`. CPU crypto instruction support is distinct from the separate CE.
The CE module, SHA hash support, AF_ALG hash support and debug counters were already
enabled; the CE clock reports 300 MHz. No module reload, kernel/package installation
or configuration change was needed.

[The bounded script](../../tests/host_crypto_offload.py) binds the exact
`sha256-sun8i-ce` driver, uses a preallocated anonymous 64 KiB mmap, checks every digest
against workstation-generated SHA-256 values for synthetic zero messages, and records
existing debug counter deltas around each batch. It does not calculate an independent CPU
benchmark on the printer. For all nine supported batches, SHA request and channel-task
increments equal the number of completed messages and fallback remains zero. The
larger-message diagnostics increment fallback and no SHA CE task. Counters are global;
the exact isolated deltas support execution when combined with successful digests.
The script status alone checks correctness/preservation, not hardware counter criteria;
the coordinator separately asserted all deltas. Its alarm starts after input/preflight;
the SSH watchdog bounds the complete invocation. Failed partial batches would need
separate byte accounting; all accepted final batches completed.

The final invocation processed 461,434,880 synthetic bytes in 5.340 seconds of internal
probe time, with a 7.084-second remote command duration. Limits were 80 seconds,
512 MiB processed per invocation and a 64 KiB reusable synthetic buffer. It measured
only hashing requests, not network transfer or storage throughput. The probe process's
CPU/wall fractions were about 42%, 24% and 20% for 4/16/28 KiB; these exclude interrupt
and other kernel-thread work and are not whole-system CPU utilization or a comparative
CPU-saving result.

An initial socket timeout failed before the first send: Python's writable polling
prevented entry to the AF_ALG hash operation. Blocking calls with SIGALRM and an SSH
watchdog corrected that invocation. A successful short preliminary run was retained
separately; its tens-of-milliseconds samples motivated the longer accepted batches.
These are three invocations, not three equally accepted benchmarks. Including the
preliminary run, 532,713,472 bytes were processed and remote command duration totals
13.832 seconds, within a 180-second/1 GiB processed lineage budget. No images or
disposable systems were created; no files were written on the guest by the probe.
Authentication/system logging remains ordinary system activity.

Before and after the final run, boot identity, root/boot read-only status and all
inspected service/mask states matched. Klipper and boot-health remained masked/inactive,
RAUC inactive. Thermal maximum was checked before each batch with refusal at 70°C.
There was no printer output, update installation, activation or reboot. No claim of
printing or release qualification follows from this measurement.

Sanitized samples, limits, counter deltas, digests, model inputs and private receipt
hashes are in [results.json](../features/h616-crypto-offload-comparison/results.json).
[The feature evidence](../features/h616-crypto-offload-comparison/evidence.md) binds
actual execution and source. The inspected kernel source files match upstream
[v6.18.51 hash](https://raw.githubusercontent.com/gregkh/linux/v6.18.51/drivers/crypto/allwinner/sun8i-ce/sun8i-ce-hash.c),
[AF_ALG](https://raw.githubusercontent.com/gregkh/linux/v6.18.51/crypto/algif_hash.c) and
[dm-verity](https://raw.githubusercontent.com/gregkh/linux/v6.18.51/drivers/md/dm-verity-target.c).
The hash driver reserves one of eight scatter entries for padding, explaining the
seven aligned 4 KiB-page one-shot limit, and sends incremental operations to fallback.
The candidate source pin is in
[kernel-61851-compile-candidate.json](../../configs/host-os/kernel-61851-compile-candidate.json).

## What an automatic update currently does

The timing model uses repository source and a representative signed compressed bundle
of **620,480,437 bytes** with a **2,348,810,240-byte** raw boot/root pair (192+2048 MiB).
The bundle size/hash come from the retained assembled-reliability build receipt; they
are an example, not a promised future release size. No historic image was copied.
Installed updater module hashes are recorded separately: they differ from the current
repository and its feed module is absent on this diagnostic system. This is a source
projection, not an assertion that this exact complete automatic flow is installed.

For a fresh successful feed download, [Feed.poll](../../runtime/sv08_feed.py) ends at
`armed-next-boot`; it does not itself request a reboot. Without an assumption about
that reboot, availability-to-ready time has an unspecified wait. The finite estimates
below assume **immediate controlled reboot, zero idle wait and successful boot health**.
Discovery/polling latency before the system knows an update exists is excluded.

Userspace SHA-256 work is `5B + 3U = 10,148,832,905 bytes`:

- One bundle pass while receiving the download.
- Four complete authenticated bundle inspection/checksum passes: receive verification,
  stage-upload lease, transaction validation and backend installation validation.
- Three raw-pair passes: source before installation, source afterward and target afterward.

The corresponding source is [staging](../../runtime/sv08_staging.py),
[bundle inspection](../../runtime/sv08_bundle.py),
[transaction](../../runtime/sv08_transaction.py) and
[RAUC backend](../../runtime/sv08_rauc.py). Raw checks read 8 MiB chunks incrementally.
RAUC's configured verity pre-check additionally reads/verifies the compressed payload
before mounting; subsequent installation reads verified SquashFS data, decompresses
and writes raw images. The [configured policy](../../configs/host-os/rauc-system.conf.in)
and pinned [RAUC pre-check](https://github.com/rauc/rauc/blob/4fb7c798d6ae412344fb8f8d310d773046af3441/src/bundle.c#L2938)
and [raw copier](https://github.com/rauc/rauc/blob/4fb7c798d6ae412344fb8f8d310d773046af3441/src/update_handler.c#L302)
explain these costs. The raw copier is not counted as another full independent hash pass.

## Specification-based planning estimate

Gigabit payload has an ideal ceiling of **125 MB/s**, so this bundle's ideal download
minimum is 4.96 seconds before protocol overhead. The installed Ethernet link reports
**100 Mbps**, whose ideal minimum is 49.64 seconds even with a gigabit source. Both
receiver assumptions are shown; no network benchmark was run.

Installed eMMC reports 8-bit DDR52 at an actual 42,857,142 Hz: the arithmetic bus ceiling
is approximately **85.71 MB/s**, shared by reads and writes. This is not sustained flash
performance. For the cold serial read/write accounting below, ideal bus transfer alone
would take about 160 seconds; caching can change the physical read volume. No storage
benchmark, cache flush or write was performed.

A conservative **serial, cold-read accounting model**, approximating compressed
payload plus verity tree as bundle size B, is:

```text
T_ready ≈ B/N + (6B+3U)/R + (B+U)/W
        + (5B+3U)/H_python + 2B/H_verity + U/D
        + F + S + L + 5 seconds
```

`N/R/W` are assumed network/read/write rates; `H_python/H_verity` assumed hashing
rates; `D` assumed decompression output rate; `F` metadata/signature/fsync overhead;
`S` state preparation; `L` restart/boot/service startup. Five seconds of stable health
comes from [boot health](../../runtime/sv08_boot_health.py). Its timeouts do not specify
successful reboot duration. Receive/install pipelining and cache hits can shorten this
serial model; shared-bus contention, slow flash, state size, retries and boot problems
can lengthen it. It is not an observed duration, guaranteed bound or statistical range.

| Illustrative assumptions | Faster | Planning | Slower |
| --- | ---: | ---: | ---: |
| eMMC read/write MB/s | 80 / 50 | 50 / 25 | 25 / 15 |
| CPU userspace / kernel hash MB/s | 400 / 400 | 200 / 200 | 100 / 100 |
| Decompression output MB/s | 200 | 100 | 50 |
| Restart/boot seconds | 20 | 30 | 60 |
| State / other overhead seconds | 2 / 2 | 5 / 5 | 10 / 10 |
| Serial total, ideal 1 Gbps receiver | **4 min 28 s** | **7 min 45 s** | **14 min 40 s** |
| Serial total, ideal 100 Mbps receiver | **5 min 13 s** | **8 min 29 s** | **15 min 24 s** |

These throughput/fixed-time inputs are **explicit planning assumptions**, not H616
benchmark results or guaranteed hardware specifications. Specifications establish
ceilings, not flash, decompression or boot performance; a reliable exact ready time
cannot be obtained from them alone. The measured CE path leaves these projections
unchanged according to consumer source routing; that is an inference, not a timed
software-versus-offload update experiment.

The planning 1 Gbps case allocates 334.16 seconds to storage reads/writes, 50.74 seconds
to Python hashing, 6.20 seconds to verity hashing, 23.49 seconds to decompression,
4.96 seconds to network and 45 seconds to boot/state/other/stable health.
As a sensitivity, assumed CPU SHA rates of 100/200/400 MB/s contribute
101.49/50.74/25.37 seconds. Those assumptions have no matched public H616 software
SHA benchmark behind them. Even a hypothetical future bulk implementation retaining
the measured 142.22 MB/s would need about 71.36 seconds for the userspace hash volume,
which is not automatically faster than CPU crypto instructions. The current CE driver
cannot provide that bulk operation, so this is a break-even illustration only.
