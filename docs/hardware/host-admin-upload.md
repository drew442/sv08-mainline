# Authenticated browser OS bundle intake

The host page now reviews and transfers a local bundle through Cockpit's required
privileged bridge and the fixed installed Python helper. Upload is private storage
intake. Its result authenticates the signed RAUC manifest and computes the whole
file SHA-256; **it does not verify every payload block, install, arm or reboot**.
Image staging remains a separate review with leased signature reauthentication,
immutable/customization/current-state checks and printer-idle admission.

## Storage and interruption

The page displays acknowledged received bytes separately from manifest checking.
One File slice and one outstanding chunk are bounded to 65,536 bytes. Display
names are at most 240 UTF-8 bytes and never become paths. Metadata is limited to
4,096 bytes, JSON output to 2 MiB and an individual browser response to 16 KiB.
Server stdin/stdout inactivity is 20 seconds, the helper's whole lifetime is
1,800 seconds, and RAUC verification additionally has 60 seconds and a combined
256 KiB stdout/stderr budget. A timer covers verification, hashing and publication
as well as transfer. The existing explicit expected-digest receive API remains.

The installed policy selects a positive bundle size ceiling; the default staging
ceiling is 1 GiB. Admission requires filesystem-rounded file allocation plus
768 MiB reserve and at least 130 available inodes. Only one managed upload or
partial may exist. Peak persistent/temporary file data is one policy-sized bundle,
plus filesystem metadata and constant lock files; atomic no-replace rename adds
no second data copy. Browser working payload is one 64 KiB slice/array buffer and
one corresponding bridge chunk, plus bounded response parsing. This is a transport
bound, not total Chromium resident memory or an assembled factory-image fit claim.

Cancellation requests helper termination; it does not cancel an OS transaction.
Graceful failure cleans only its own unpublished file. SIGKILL can retain an
interrupted partial, while a lost final response can leave a published bundle.
Reconnect lists actual managed objects and busy state without replay. The owner
separately reviews removal of an exact object. Linked, replaced, stale, ambiguous
or operationally referenced objects are refused. A completed/cancelled update's
bundle can be removed once state, current boot and backend postconditions agree;
historical receipts/journal remain intact. Terminal cleanup uses the real backend’s
existing immutable-root/identified-device checks and a shared ten-second command
observation deadline. Writable intake and removal of never-staged uploads do not
need that backend context; terminal cleanup can refuse until an immutable boot. Failed/uncertain transaction material
still requires the separate reconciliation workflow.

The [lock and verifier lifecycle decision](../decisions/0013-bounded-browser-bundle-intake.md)
explains why ordinary status/history/policy operations remain responsive during
transfer, image submission refuses busy intake before receipt creation, and a
supervisor retains the upload lease until all verifier descendants are gone.
If a verifier is stuck in the kernel, busy state persists honestly instead of
allowing cleanup underneath it. Missing installed host context, policy, keyring,
upload directory or valid registry produces refusal without initializing state.

## Reproduction and evidence boundaries

Use the selected [actual Cockpit fixture](host-admin-cockpit.md), exact baseline
and pinned delta archives. Build a small synthetic signed fixture with
[the fixture generator](../../tests/upload_fixture.py), then pass its directory
as `--upload-fixture` to `tests/cockpit_fixture.py prepare`. That option copies
only the public certificate and fixed synthetic policy into the guest; the
signing private key stays in the private workstation fixture. The browser reads
the generated `signed.raucb` file through the actual file picker.

The optional upload guest is a sparse **3 GiB** single-root ext4 image. The first
2 GiB experiment correctly refused low space with the unchanged production
768 MiB reserve; increasing only the disposable guest permits testing intake.
Tiny 256 KiB raw boot/root payloads target `sv08-upload-fixture` and
`upload-fixture-v1`, not a real SV08 layout. No update backend/device configuration
is staged, so this guest cannot install images or establish factory 8 GB fit.
Native RAUC 1.15.2 creates the verity bundle; the actual ARM64 guest uses the
selected Debian RAUC 1.13 for manifest authentication. These versions are recorded
separately and no general compatibility claim is made.

The [real browser cases](../../tests/cockpit_upload_cases.mjs) extend the actual
Cockpit/PAM/sudo suite with review cancellation, progress/publication, tampered
signature refusal, paused helper responsiveness, transfer cancellation, process
death, lost final acknowledgement and authenticated reconnect/explicit cleanup.
Fault injection delays a browser File slice or filters only the final actual
response; it does not replace authentication or the RAUC verifier.

The [runtime cases](../../tests/test_admin_upload.py) cover lock ordering,
queued/running/interrupted job exclusion, no premature receipts, exact-object
cleanup, distinct successive releases and retained history, leased reauthentication
and idle guards, metadata/time/output limits and parent-death exclusion. A
supervisor is deliberately paused to prove that helper death alone cannot release
the inherited lease before descendants are killed. The
[protocol cases](../../tests/upload_protocol.mjs) independently check fragmented,
malformed, oversized and wrong-offset acknowledgements and measure the single
64 KiB window. [Native signed-policy cases](../../tests/upload_signature_checks.py)
reject wrong profile, layout, state schema, MCU/host Klipper pin, size, tampering
and an untrusted keyring. Native unit doubles are labelled as such.

The [2026-09-12 execution record](host-admin-upload-20260912.json) records all
actual Cockpit cases passing, matching installed source hashes, 55 administration
unit cases, 56 additional integration cases, and all three existing Chromium
suites. The signed fixture is 542,650 bytes; the 3 GiB guest allocated
1,414,422,528 bytes after testing. Runtime/host-UI source payload grows from
192,488 to 220,237 bytes (27,749 bytes). UI-stage inventory additionally includes
31,720 bytes of pre-existing core modules; that accounting expansion is separate
from code growth. The native signed-policy suite measured 19,768 KiB maximum RSS;
it does not measure total browser memory. Protocol tests observe a 65,536-byte
maximum slice and outstanding window. No second payload copy is published.

Retained reports/logs were scanned for synthetic passwords and Basic encodings;
none were found. QEMU stopped, workstation identity/service state was preserved,
and the guest image, guest credentials/browser profile and signing private key
were removed after retaining sanitized evidence and public fixture certificate.
 Hardware, release, production accounts/TLS and assembled
image acceptance remain in the [canonical checklist](host-os-tasks.md).
