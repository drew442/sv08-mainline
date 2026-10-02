# Secure early-boot entropy acquisition for H12

## Requirement and observed failure

Complete the existing authenticated preflight without weakening unpredictable
challenges, signed purpose, expiry, target admission, one-shot consumption or
recovery. This is an offline repair; it grants no physical-operation authority.

The October 2 physical job reached trusted RAM Linux and reported
`CLAIM_RANDOM_TIMEOUT errno=110`, then refused the claim and rebooted into the
original p5 kernel. The server claim remained unused. No preflight passed.
The 110 is the helper's local ETIMEDOUT; individual kernel errno values were not
recorded. Unready kernel randomness is the leading explanation, not measured proof.

Current acquisition polls getrandom(GRND_NONBLOCK) before any socket is created.
Linux 6.18.51 returns EAGAIN from this path before wait_for_random_bytes(). Blocking
secure acquisition enters wait_for_random_bytes(), which can invoke upstream
try_to_generate_entropy(). This is useful at initramfs PID 1 before root services.
Selected hardware RNG/provider availability remains unknown.

Primary source: [Linux 6.18.51 random.c](https://raw.githubusercontent.com/gregkh/linux/v6.18.51/drivers/char/random.c),
accessed 2026-10-02. This source behavior does not prove successful entropy
collection on the owner-reported H616_JC_6Z_V1.2 board.

## Proposed bounded change

Use supported blocking getrandom with flags zero and exactly 32 secure bytes,
under the existing single 60-second CLOCK_MONOTONIC acquisition deadline.
A caught monotonic POSIX timer signal, without SA_RESTART, may interrupt the
blocked call. Check the original deadline before completion and retries; retain
partial reads. Account for PID 1 signal behavior, inherited masks/dispositions,
setup failures, deadline races, cleanup and transport socket isolation.
If interruption cannot be reliably demonstrated, stop and return an alternative
bounded design for review rather than shipping an unbounded blocking call.

Do not credit supplied seed bytes, use weak/deterministic production randomness,
increase the deadline, change claim protocol or add request/job retries.
No network/target operation occurs until all 32 secure bytes are admitted within
budget. Keep concise nonsecret stage/errno diagnostics. Preserve existing source,
failed candidates and historical test results.

Owned implementation paths: tests/fixtures/sd-network-root/emmc_image_writer.c,
tests/test_emmc_claim_startup.py, and a new evidence document
 docs/development/h616-claim-entropy-acquisition-20261002.md.
Use libc/kernel timer and signal APIs; no new installed runtime dependency.
The custom helper retains its existing commissioning retirement plan.

## Acceptance

1. Actual compiled helper exercises ready, interrupted, partial, unavailable,
   setup/clock/cleanup failure and exact-deadline cases; no challenge in diagnostics,
   no socket/target access before completion, at most one subsequent claim request.
2. Demonstrate real signal interruption of a blocking syscall within budget,
   including an actual PID 1 Linux fixture if available. Source-only or ordinary
   process tests must not be presented as PID 1 proof. An unverified interruption
   boundary prevents physical candidate acceptance.
3. Retain relevant authenticated receipt/no-random/purpose regression coverage and
   ARM64 compilation of affected modes. Reuse unchanged prior evidence explicitly.
4. Independent delivery verification of full diff and evidence before physical
   artifact preparation. Actual fresh signed challenge/receipt/single consumption,
   preflight PASS and required original recovery return remain physical gates.

The physical queue is stopped after the failed attempt. USB power-off confirmation
and a separately reviewed recovery operation remain coordinator responsibilities;
no cold-capture or UART-input work is reopened.
