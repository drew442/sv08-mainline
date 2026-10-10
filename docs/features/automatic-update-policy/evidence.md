# Automatic update policy and activation evidence

Date: 2026-10-10. Baseline: `43a104d`. Executed source freeze:
`af70d6d2bda5913dda16f77bfc31d2df08c32a22`.
The final candidate adds only this report and its sanitized results to that freeze.

## Delivered behavior

Automatic updates require trusted CMS signatures for both feed metadata and the
RAUC bundle. Cockpit exposes separate compatibility-label, customization,
release-version and downgrade choices. A manual provenance exception is reviewed
for an individual upload/staging operation; it does not alter the keyring or
automatic policy. Mathematical signature and payload verification remain required.
Missing/malformed CMS and literally signature-free files are not supported.

Signed positive release revisions provide ordering; feed publication sequence and
display identifiers do not. Existing releases without a revision require an
explicit version-check exception. Transactions bind their origin, exact policy,
signed revision and admission proof. Stage, arm and automatic reboot recheck them.
Physical layout/device identity, inactive target, capacity, recovery, immutable
source, printer idle admission, source preservation and readback are unconditional.

The production feed now requests a controlled reboot after staging and arming.
State/network/admission locks serialize policy changes and competing operations.
A durable receipt distinguishes undispatched, queued, uncertain and observed
requests. Uncertain dispatch keeps admission closed and is not replayed. Opt-out
before dispatch retains the armed update and suppresses automatic reboot. Existing
boot health confirms the trial or reconciles fallback. Undispatched terminal
receipts are retired so cancelled work cannot prevent later discovery.

## Native and browser checks

The focused native suite passed 307 tests in 73.744 seconds on `c1afe95`.
After the four-file review correction, the affected automatic reboot/feed/
transaction suite passed 66 tests in 13.090 seconds on `af70d6d`. These are
overlapping checks, not 373 unique tests. Strict policy schemas, manual/automatic
origin separation, current source-version admission, opt-out, cancelled-receipt
discovery, competing jobs, launch failure and interrupted/uncertain dispatch were
checked. An independent targeted reviewer reproduced eight causal regressions.

Actual native patched RAUC passed 16 info/install cases using private D-Bus,
regular-file paired slots and a private mount namespace. Default unknown signers
were refused; the reviewed exception accepted an unknown signer. Damaged
mathematical signature, malformed/missing CMS, damaged verity payload and wrong
manifest binding were refused before writes. The successful exception preserved
the active pair and primary selection, matched the inactive pair and did not
weaken a subsequent strict install. Untrusted hook SPKI metadata remained empty.
RAUC info authenticates the external manifest; it does not establish complete
payload verification. The damaged-payload info case therefore succeeds, while
installation fails before writes.

The native executable SHA-256 is
`ca52fcfb2a8e5a38f5e3868bc62e3aa14af8cff5bfec3b649ec0c7189036b85b`.
The pinned patch SHA-256 is
`75b465c83ad9e40e5d32b9bc79a42232ecf2a2edca61c2a05fadee1fdcf49258`.
Its source archive, toolchain and package identity are recorded in results.json.

Actual Chromium exercised the Cockpit assets with a localhost fixture: advanced
automatic settings persisted through the real Controller, drafts survived polling,
manual staging/upload reviews bound their distinct options, and desktop/mobile
rendering produced no runtime exceptions. Manual review responses were
instrumented; this browser run does not claim authenticated installation. Native
backend and real RAUC checks provide those separate layers of evidence.

Python syntax, JavaScript syntax, changed documentation links and diff whitespace
checks passed. No submodule/gitlink, file-mode or source deletion changes occurred.
Package/source patch hashes agree, and image staging derives the service identity
from the actual installed ARM package and executable rather than relabeling the
old service-policy hash.

## Disposable ARM journey and storage

The actual ARM package `rauc_1.15.2-0sv08.2_arm64.deb` built successfully:
package SHA-256 `fc1d757cbe91b39d59f1e4f6634d77016748929ac17849f2047935a4f620f0ec`,
installed executable SHA-256 `2d4a14c0371a28e0a81255a3a9a9de901a5fa4b6c24b6530ab2aef37e0ba40ba`.
GCC 14.2.0, Meson 1.7.0, Ninja 1.12.1 and OpenSSL 3.5.7 were used in the
disposable Debian ARM compiler. Dependency archive hashes and setup/build commands
are retained in results.json. The compiler filesystem was retired before testing.

One bounded six-boot journey passed against frozen `af70d6d` bytes:

| Boot | Slot | Observed outcome |
| --- | --- | --- |
| 1 | A | Trusted signed feed installed/verified revision 2 in B, armed it, and production automatic restart requested reboot. |
| 2 | B | Production health confirmed revision 2; settings, identity and source customization were preserved. A second trusted feed installed/armed revision 3 in A and requested reboot. |
| 3–5 | A | Injected health failure exhausted three real environment attempts. The health readiness gate stayed closed and the transaction was not confirmed. |
| 6 | B | Production preparation/health reconciled the failed trial and restored the preserved working generation. Failed-target configuration did not leak into it; the reboot receipt was observed. |

Actual bundle CMS verification, RAUC paired inactive writes/verity/readback,
production controlled restart, systemd, state preparation and boot health ran.
Transport and printer idle services were simulated. The host selected boots by
consuming real redundant environment counters; SPL/U-Boot did not execute.
For failed health, the existing disposable fixture substitutes a fallback marker
for production's reboot callback so the guest can check the closed gate and
unconfirmed journal; the guest then requests an actual systemd reboot.
Persistent CA, SSH public identity, machine identity, owner configuration and
shared user sentinel were preserved. GPT metadata, recovery and shared base hashes
matched before/after. Exact boot/log/fixture/source hashes are in results.json.

Codex and Beelink free space were checked before image work. Testing used Codex,
one live GPT disk and sequential disposable construction rather than historic
copies. The primary lineage retained conservative compiler charges of 700 seconds
and 6 GiB; deletion did not reset its allowance. Limits were 3600 process seconds,
32 GiB cumulative allocation and 16 GiB free-space floor. The initial 6 GiB live
guard stopped the first journey during boot 2 after healthy confirmation but
before the second installation completed. Its 6,535,647,232 allocated bytes
exceeded the cap by 93,196,288 bytes; runtime, cumulative data and free-space
bounds remained satisfied. The failed attempt is retained as incomplete. Root
raised only the live host ceiling to 10 GiB, archived its byte-identical receipts
and retired its partial disk. A fresh initial media and six new boots completed;
the interrupted installation was not resumed and its boots are not counted as
accepted final boots. Runtime/allocation ledgers carried all prior charges.

The fresh media reused the preserved synthetic fixture signing/owner identities
and existing signed bundles. A logged disposable invocation wrapper intercepted
only the two exact fixture identity-generation commands, with public identities
hash-checked before/after. Its hash and intercepted arguments are in the repair
receipt; production source and the executed guest fixture bytes remained af70.
The 10 GiB test-host ceiling does not change factory device/layout constraints.

Actual final
runtime, cumulative allocation, reclaimed bytes and free space are recorded in the
retirement receipt. Goal-owned disk, root template, bundles and ephemeral fixture
identities were retired after the final consumer exited; logs, hashes and the small
ARM package remain. Shared bases and unrelated historical artifacts were preserved.

## Retained failures and limits

The initial native RAUC fixture compressed into an unsupported 4096-byte squashfs;
using 64 KiB of random image data corrected that disposable input. Initial browser
fixture ancestry permissions and a harness string-generation error were corrected
before the accepted run. The first added cancellation test omitted the fixture's
owner_uid; correcting that test setup produced the passing regression. Failed
logs are retained locally and are not counted as successful runs.

The unchanged broader test_admin_history_repairs suite has five missing-store mock
errors among seven tests. An exact `43a104d` checkout reproduced those five errors
in 0.549 seconds. Production jobs/history code and that test were unchanged;
the focused affected checks above passed. The initial flat-PYTHONPATH comparison
loaded current runtime and is not used as baseline evidence.

The ARM package build emitted a dpkg-shlibdeps directory warning and exited zero;
upstream native OpenSSL/CURL deprecation warnings remain recorded. Offline evidence
does not qualify physical power cuts, the H616 SPL/U-Boot path, printer hardware,
heating/motion/printing or release distribution. No physical printer update,
reboot, service change or output activation occurred for this goal.

See [product contract](../../development/automatic-update-policy.md),
[owner scope](owner-request.md) and [sanitized results](results.json).
