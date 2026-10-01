# h616-claim-startup-readiness: handle temporary early-boot RNG unavailability

Requirement: preserve the accepted authenticated one-shot claim and fail closed
when secure randomness is unavailable. Complete the already authorized H12
preflight; no changed hardware, crypto, signing, target or recovery requirements.

Reproduction: physical job C entered trusted RAM but reported only
`REFUSED_OR_UNCERTAIN_CLAIM`, with the server claim unused. The unchanged client
uses `getrandom(GRND_NONBLOCK)` and immediately returns on EAGAIN before opening
a socket. One source reproduction establishes that mechanism; actual physical
errno remains unknown, and TCP failure remains an alternative. The serial
capture lacks a CRNG-ready message. This is a diagnosis to test, not proof.

Change: in `tests/fixtures/sd-network-root/emmc_image_writer.c`, allow a bounded
monotonic wait (at most 60 seconds) for secure randomness on temporary EAGAIN,
with interruption/partial-read handling and a deadline checked on every retry.
Keep GRND_NONBLOCK, obtain all 32 bytes before generating the challenge, and
retain refusal on permanent error, zero read or timeout. Add concise stage/errno
diagnostics for randomness, socket/connect/send/receive and receipt refusal.
Never print random bytes, challenges, signing keys or credential contents.
No HTTP request retry, automatic job rearm, alternate weak source, busy spin,
new dependency, target-admission change or boot-policy operation is included.
The wait may time out on a genuinely unavailable RNG; it does not seed or claim
to initialize hardware RNGs. Physical H12 recovery remains separately reviewed.

Validation: exercise the actual compiled helper, including immediate availability,
temporary EAGAIN then readiness, EINTR and partial success, permanent EAGAIN
through the deadline, other errors and zero reads. Demonstrate no socket/send
before a complete secure challenge and at most one HTTP request after readiness.
Retain existing valid/forged/replayed receipt and no-random refusal coverage,
compile relevant ARM64 modes and measure binary/FIT headroom. Use a deterministic
clock/syscall fixture for the deadline; do not spend 60 seconds on mirrored tests.
Keep preflight-only and ordinary diagnostic purpose distinctions. Independent
delivery verification is required before building any physical candidate.

Human dependency: current SPL halt needs the prepared USB reset/SD return in
H12 of `docs/hardware/coordinated-human-tasks.md`. No physical reset, new job,
claim service, eMMC/MCU write or printer output is authorized by this offline fix.

Provenance/retirement: this is a correction at the existing custom commissioning
claim boundary, using Linux secure RNG interfaces and the pinned crypto library.
It inherits the existing commissioning-helper retirement plan; temporary fixture
and diagnostic scratch do not become host-image dependencies.
