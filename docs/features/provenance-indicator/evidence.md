# Installed provenance indicator — 2026-10-27

Source & license previously showed recorded build metadata without checking current installed bytes. It now displays an outline icon and labeled status: green **Intact**, red **Tainted**, or neutral **Checking/Unavailable**, with a short explanation. On open and Check again, the shared build/runtime validator compares the current project-file inventory, SHA-256 hashes, build identity, release, public-key build input and notices/copies to the local record. Persistent user/printer configuration remains outside the existing inventory scope. No background polling or image hashing is added.

The existing finite read channel has one new fixed provenance/status operation. It reads protected covered files (including sudoers0440) without an administrator bridge, exposes only state/build_id/scope/reason, and accepts no caller-selected root/path. Its isolated Python child uses -B to prevent bytecode mutations. Ordinary document blob links and matching-public-source qualification remain separate. An intact local record establishes consistency, not publisher authenticity, whole-OS integrity or hardware readiness; a coordinated rewrite of verifier and baseline is not detected as an attack by this consistency mechanism.

## Acceptance and actual results

| Check | Observed evidence |
| --- | --- |
| Genuine baseline / covered drift | Shared validator and real staged fixture: clean intact; changed/added/deleted covered code, notices, release and malformed/mismatched/deleted package record tainted. Missing primary baseline, permission/walk errors unavailable; never green. Mutable user configuration excluded. |
| Read boundary |13finite-view tests pass: exact allowlisted request/command, sanitized finite response, no arbitrary path/module/mutations or administrator bridge. New helper is part of host/printer staged inventory, report and rollback coverage. |
| Browser journey |Final composed browser c exit0,5.125s; actual isolated Python verifier subprocess through finite view adapter. Intact→Tainted→Unavailable→Intact, immediate Checking on retry, delayed old intact cannot overwrite newer tainted, command/JSON failures neutral, checked/displayed build mismatch tainted. All three documents still open exact text in new tabs; no elevation, controller mutations, bytecode or root byte/mode/link changes. Unrelated saved configuration and unsaved draft preserved. |
| Keyboard / layout |Actual renders inspected by skilled implementer and coordinator:1280px desktop and390px narrow. Opening/retry focuses title and scrolls to status; keyboard retry, Escape/opener focus, no horizontal clipping. Narrow links/actions require normal vertical scrolling. Icons supplement text and traffic-light color; none added to heading. |
| Standard regression |`python3 -B -m unittest discover -s tests -p 'test_project_license.py' -v`:21PASS,0.715s (18existing+3new runtime tests, combined into the existing package/release CI suite). `test_config_view.py`:13PASS,0.245s. `test_source_policy_ui.py`:2PASS,0.001s. `test_stage_admin_ui.py`:22PASS,3.761s. `test_stage_printer_ui.py`:13PASS,70.346s. Total71distinct tests; Node22 syntax and diff checks pass. |

The focused view/source-policy results are retained in implementer tool observations68613e/59fc4d. New runtime cases were initially run separately (3PASS); coordinator moved them unchanged into existing test_project_license.py so the standard package/release CI gate actually discovers them. Final21-test log retained. Product/verifier/browser bytes remained unchanged by this test-only relocation, so final browser/staging evidence is reused rather than repeating unchanged behavior.

## Attempts, ownership and limits

Research `/root/provenance_trace` used named project_researcher with omitted effort (configured Sol/low); skilled `/root/provenance_implementation` used named project_implementer with explicit medium and fork_turns=none. The child explicitly read repository sv08-ui-ux SKILL.md plus relevant reference, kept implementation/test/rendered judgment together. Settings requested/profile configuration are recorded; this delivery did not instrument effective model/effort telemetry or measure savings. One active implementer, no delegation. Self-validation, not independent review.

Primary allowance1200cumulative process-seconds/1GiB; scratch `/home/drew/.sv08-provenance-indicator`, approximately8.1MiB retained before this evidence. Existing Node22/Chromium only; no installs/images or printer operations. Research used no experiments. Existing project task was blocked/resumed with preserved source, history and cumulative allowance solely to renew ownership for protected finite reads; native goal stayed active. No auth/sudoers policy changes.

Retained failures: browsera never started because coordinator scratch ancestry was0755; corrected assigned scratch to0700 without weakening admission. Browserb passed behavior then caught test-created baseline recreation changing0644→0664. Test repair restores captured original mode, retaining full no-mutation assertion. Rendered b also exposed autofocus scrolling status out of view and transient narrow capture; source fix focuses the title at load start (never async completion), shortens neutral copy, and tests wait for settled visible status. Finalc and final affected staging pass. Earlier22+13 staging passed before that concrete UI correction and is retained separately.

Browser transport/session and installed root/import location are fixture adaptations; real subprocess hashing and finite view filtering execute. This is not actual installed Cockpit/PAM, production TLS, H616 timing, malicious-tamper attestation or hardware qualification. Check is point-in-time; unreadable/missing baseline cannot prove integrity. No automatic merge or deployment. The goal ends at a tested published review PR; feature task remains validated awaiting owner integration.

## Artifact hashes

Private sanitized evidence remains under the scratch path; exact product/test inputs are bound by the feature record to the final commit. No credentials or image artifacts were generated.

| Path | SHA-256 |
| --- | --- |
| `integrity-final.log` | `68becd10180b729183c09a59ed88d6a3494a3a507312c2e1a95a89c90e550998` |
| `stage-admin.log` | `7f8e25c224bd50ff1bfeca1d827290b445ccdf7c7dfa8c86d0566aac7e840a3f` |
| `stage-printer.log` | `044077f3cb8c739cfc18e28794776c3796ee78c3eb3c050c17abe8d4f61ec835` |
| `stage-admin-final.log` | `fcbb91549bb7d2cecdbe9acab44a9a9f7e31320b4d2d62021950363cd2c42be1` |
| `stage-printer-final.log` | `3892fcfc6672f862311b5d00592a6f6a1e0d5b3aeaca3d121d91e9d9d572afb8` |
| `server-a.log` | `b09264bbe0d312562bda66c77e0aa9a51ef6c4b9a00920ca4d592f8baec71686` |
| `run-a.json` | `2b0b088d2cafb3b7e867179f3b6347eb70f48c8bae8855646e8b131886e17b02` |
| `browser-b.log` | `0c1480ff92f8c204d225984988908d499842b20c47cc12146e408da487e32177` |
| `run-b.json` | `48fdc6d09fd51f6263ba699be7905e8bc5754e150e1cee6212a71924d9b1fa01` |
| `run-c.json` | `26b8ac37663bcd6d025d0d16a472436be74b06e46662a990e9d1ea2759b87ebd` |
| `browser-c/summary.json` | `e05d336b9c1b48c2922f9e316be83f8ed9d1669369af8c7db6bc340e7b6221d8` |
| `browser-c/source-narrow.png` | `69c6514e46644a99f3a2b24eefdde1ce06a28d72b8a0a40c6001c8c98e8ce2ef` |
| `browser-c/source-tainted.png` | `be1a74ac895a346ed8af7de9b3664c5b67b898811e33c3ae22eef69db6c832f0` |
| `browser-c/source-baseline-unavailable.png` | `939ee663f670846fb48e6007e9522b071e2ad59690463999ded2abff0aef3c29` |
| `browser-c/source-unqualified.png` | `b59d80972e3bf90ebde7b3fecc79f6dbab6f107173aeb7cee100ca4a85b97170` |
