# Cockpit UI/UX implementation evidence

Owner authorized implementation of W0–W8 and revision of all presentation and
interaction choices, preserving core capabilities. This delivery is self-validated
under the proportionate review policy. No printer operation or deployment is included.

## W0 capability map and interaction sketches

| Destination | Primary interaction | Retained secondary capabilities |
| --- | --- | --- |
| Overview | Current host state and corrective task links | Storage, release/mode state, compact unresolved-operation links |
| Hardware / Components | Choose fitted parts, review configuration, separately review application | Factory selection, board identities, advanced device/pin/sensor settings, calibration values, custom configuration/macros |
| Hardware / Changes and draft tools | Inspect semantic changes or save an incomplete draft | Output modes, generated text and complete configuration ZIP, inactive candidate export, shareable import/export, history, previous-candidate restore, legacy migration, publication restore/reconcile, uncertain-save reconciliation/discard |
| Hardware / Find definitions | Search source/category and drill into details | Provenance, versions, supported/unavailable state; deliberate use in hardware |
| Hardware / Definition sources | Preview then add/update a repository | Local bundle import, pinned ref/path, check updates, enable/disable/remove sources, author starter ZIP and schema ZIP |
| Hardware / Connections | Filter a signal and inspect its logical mapping | Graph tracing, pan/zoom/layout, documented contact details, explicit unknown contacts |
| Updates | Running/fallback release, automatic policy and manual update stages | Scoped manual exceptions and automatic checks, upload review/progress, installation/next boot/cancellation, operation receipt/history/reconciliation/maintenance |
| Network | Current connections and selected interface | Scan/select WiFi, saved/new wired/wireless settings, IPv4/DNS, hostname/FQDN, reviewed restart, reconnect links, confirmation deadline and rollback |
| Access & identity / Mainsail login | Choose password/no-login/client certificate | Certificate creation/download/revocation, explicit provisioning order and no-login consequences |
| Access & identity / Printer trust & identity | Trust public CA and manage SSH public keys | CA and SSH fingerprints, private identity backup and reviewed restore |
| System & recovery / Operating mode | Review immutable/writable choice | Preserve customization and explain next boot consequences |
| System & recovery / Additional software | Review supported package/service operation | Installation/removal, writable/idle/storage prerequisites, interrupted-result resolution, service settings, customization/compatibility reports |
| System & recovery / Recovery | Reach documented independent recovery tasks | Display-driven preserved system/replacement/data recovery guidance |

All destinations share one Cockpit session: authorize, end administrator access,
log out and refresh. Historical hashes remain supported contextual entry points.

The bed/source sketch is Hardware → bed component → add source → inspect preview
→ add catalogue → return to the same component → inspect definition effects →
confirm local selection → review configuration → prepare saved inactive candidate →
separate application review → explicit application. Preview/cancel changes no stored
draft; source import alone never selects hardware. Cancelling application retains
the saved candidate and labels it inactive. Failed or uncertain writes lead to
reconciliation instead of an automatic retry. Calibration remains separate.

The connection sketch is Hardware → Connections → filter sensor signal → select
mapping → inspect board/signal and known contact details → optional graph tracing →
return to hardware. Unknown physical contacts stay unknown; exploration is non-mutating.

The access sketch shows current method → choose one method → enter only its needed
inputs → review consequence → confirm → refresh confirmed state. Client certificates
are downloaded/imported before enabling certificate login. Public CA trust, personal
client authentication, SSH authorization and Cockpit elevation are distinct.

The update sketch is Updates → automatic opt-in review or manual upload review →
verified stage → next-boot review → restart/health outcome. Cancellation retains the
policy draft; uncertain acknowledgment exposes the same operation receipt. Advanced
checks remain scoped to policy or one reviewed manual operation, with backend
mandatory protections unchanged.

Assessment is expert source/rendered assessment at desktop, printer-screen, phone
and zoomed sizes. No measured human usability result or full accessibility certification
is claimed. Final screenshot/test bindings and outcomes are recorded below.

## Validation and limits

Product source is frozen at `0d16b6259486904ac07dd8c4a00f59df3eb87cc0`.
[evidence.json](evidence.json) binds the source, 31 workplan acceptance checks,
public fixture receipts and coordinator rendered assessments. These are expert
source/rendered and disposable execution results, not human task observations.

The implementation worker used the actual `project_implementer` profile with
explicit Sol/medium for scoped UI work. A fresh `project_integration` worker used
Sol/low with a compact installed-check handoff. Runtime role/model/effort evidence
is retained in the coordinator's `dispatch-runtime.json`; no agent configuration changed.

Successful checks: 12 printer staging and 5 printer-controls tests; 20 final host
staging tests; the full printer browser journeys; shared shell keyboard/touch;
draft/selection freshness; automatic policy and scoped manual options; Network,
Mainsail and Software service-browser tests; real disposable Identity tests;
update jobs, interrupted outcome resolution and history maintenance/pressure tests.
The browser source receipt precedes two final footer/history corrections; final
focused reflow and history/empty-source checks cover those deltas. Service backend
inputs were unchanged. Screenshots are assessed at 1440×900, 1024×600, 390×844 and
512×300 CSS pixels with scale factor 2 for enlarged-text reflow. Body-style zoom
captures are supplementary, not native browser zoom proof.

The update job fixture used a real independent host user systemd worker, real
Controller/Transaction, a disposable disk double and a test-only verifier. Lost
acknowledgment retained one receipt/installation; reopening connected in 128 ms.
Unknown-outcome resolution preserved the source and made zero installations.
History tests preserved 128 original rows, retained unknown submissions on durable
read failure, cancelled once, survived real tmpfs space pressure and reconnected
across a separate worker's state lock in 115 ms. All production floors, receipt,
transaction and backend nonmutation assertions remained intact. Legacy fixture
signer/release metadata and navigation were corrected in scratch; reusable test
maintenance is recorded as a separate coordinator followup, not silently added to
this task's ownership.

Idle Hardware made 13 baseline versus 0 candidate host RPC calls over the same
6500 ms settled window. This establishes request counts only; no host CPU or
end-to-end performance improvement is claimed. Urgent work retains faster refresh.

Installed native Cockpit/PAM acceptance is recorded separately below. Production
network changes, identity restoration, live hardware publication, heating, motion,
printing and updates were not exercised or authorized by this delivery.
Private browser profiles, credentials and generated disk images are not published.

A targeted source researcher resolved one installed-test assumption: [the session
decision](../../decisions/0012-cockpit-session-integration.md) delegates authority
to Cockpit and requires explicit elevation, Stop/logout and fail-closed local
authority. Existing `tests/cockpit_browser.mjs` accepts a retained elevated shell
within the same login session, then separately requires denial after Stop and
a fresh login. Same-session reload was therefore recorded as retained native
authority, rather than adding a requirement to prompt on every page load. The
original unsupported expectation remains in the failed fixture receipt. No
product authentication behavior was changed to pass a test.

## Installed native boundary check

Actual Cockpit 337/PAM/sudo passed in disposable ARM64 QEMU against frozen source
manifest `395d2128f42b360da1396410400efb97528409116e0e66035fcda20dc8bf5717`.
Ordinary UID 1002, unelevated administrator UID 1001 and explicit elevation to UID 0
were measured. Bad login, ordinary mutation, wrong password/cancellation, End access,
reload after End access and fresh-login privilege denial passed. Twelve routes,
Back, non-secret source-URL/Mainsail-method continuity and fail-closed local authority
after transport close passed. Same-login reconnect observed Cockpit's retained
explicit grant; no new automatic grant was started.

Native screenshots did not await settled host/printer status after reauthorization:
they show transitional authority wording and empty legacy hardware state. They
support shell/no-overflow/history visibility only. Settled status and populated
factory-layout acceptance use the real disposable Controller/PrinterStore composed
browser evidence. No native browser zoom or human usability evidence is claimed.

The old synthetic guest required disposable input corrections: sanitized inherited
identity, exact public source staging, socket readiness, inert identity prerequisite,
fresh self-signed HTTPS, strict legacy RAUC policy and synthetic Mainsail status-only
files. Production identity/TLS trust, network mutation and updates were not tested.
Backing hash `b08c18e3f39e7096c4faeb047f1e26fb5db593dc3d0ff451658eb4b528a8ad43`
remained unchanged. Owned credentials, guest images/profiles and processes were
removed; the evidence scan found no generated fixture password or Basic encoding.
Recipe/extraction time was 924.72 seconds; conservative total with planning below
1100/1800 seconds. Cumulative allocation upper bound was 2,346,471,424 bytes/4 GiB.
Public receipts and exact staged hashes are embedded in evidence.json. This is
installed execution evidence, not independent approval or printer readiness.
