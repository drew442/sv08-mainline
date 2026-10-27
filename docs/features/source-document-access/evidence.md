# Source document access — 2026-10-27

The owner reported all three public document links returning Not Authorized and the dialog reporting installed source information unavailable. Previously the dialog fetched provenance and opened documents using separate HTTP requests. The candidate reads exactly the three installed public files through ordinary authenticated `cockpit.file`, closes handles, and opens browser-local text documents. It requires no administrator access, controller operation or new anonymous endpoint. Source qualification checks remain unchanged. A failed read removes stale links/offers, reports retry guidance and leaves other readable documents available.

## Observed acceptance

- Composed panel browser: PASS at1280 and390CSS-pixel widths. Raw HTTP documents deliberately return401; the ordinary authenticated file adapter remains usable. All three links open via keyboard into new tabs with exact installed document text. No elevation/controller mutations; saved state/configuration bytes and unrelated unsaved network input remain unchanged. Escape returns focus; malformed and failed provenance remove stale public-source offers; independent license/notice reads survive. Controlled offer rendering is not public-source qualification.
- Actual disposable ARM64 Cockpit/PAM: PASS using fixtureordinary, with privileged access denied. After removing only the synthetic browser HTTP cookies, raw provenance HTTP returns401 while the established authenticated ordinary bridge reads all three fixed files. All three new-tab texts equal installed files; no elevation and unrelated draft input preserved. This reproduces the failure class; it does not establish the cause of the owner's missing HTTP authorization.
- `python3 -m unittest discover -s tests -p 'test_source_policy_ui.py' -v`:2PASS.
- `python3 -m unittest discover -s tests -p 'test_project_license.py' -v`:18PASS.
- `python3 -m unittest discover -s tests -p 'test_stage_printer_ui.py' -v`:13PASS.
- Node22 syntax checks for both changed browser drivers and `git diff --check`:PASS. Complete stable source diff inspected by coordinator; self-validation, no independent review claimed.
- Rendered images actually inspected: narrow ordinary dialog, partial-failure feedback and actual Cockpit document links. Text/link wrapping, keyboard focus and scrollable dialog remain usable. No redesign is claimed.

## Attempts and fixture limits

Scratch: `/home/drew/.sv08-source-links-20261027`;1800process-seconds/4GiB primary allowance, one2GiB root copy and one1.5GiB data image, existing Node22/Chromium/QEMU. No OS rebuild, installation, physical output or live printer mutation. Synthetic accounts only; credentials consumed programmatically, never published.11own installed evidence/log files scanned:0synthetic credential violations. Synthetic credentials and newly generated root/data copies removed after evidence capture. Cleanup confirms QEMU stopped, private namespace removed and host identity/Cockpit units preserved.

Failed attempts are retained. First composed test reached exact document tab checks then incorrectly counted routine background status reads as mutations; corrected to exclude only existing read-only host status/jobs/upload.list while preserving the no-mutation and byte-equality assertions. The actual test first assumed UID1002, but this synthetic fixture uses1001; corrected to assert account identity fixtureordinary, retaining privileged denial. Both corrected runs pass. Fixture preparation encountered restrictive vendor-branding symlink and missing old provenance inputs; only the copied guest's vendor asset symlinks were normalized to identical bytes with targets/hashes recorded before generating genuine project metadata. Initial boot refused copied image ownership; assigned copy ownership was corrected. Server/PAM/sudo/transport auth policies were not changed.

Actual installed test uses private HTTP and emulated disposable ARM64, not production TLS, owner's browser/session or physical hardware. The three installed public documents must exist/readable by the ordinary account. A fully disconnected Cockpit bridge still requires reconnection/sign-in. This PR is source delivery only: no merge or deployment. Public matching-source qualification remains independent and may truthfully report unqualified.

## Retained evidence SHA-256

Private sanitized logs/screenshots remain at the scratch path; hashes below bind observed results and visual evidence. Product/test source is bound by the feature record to the final candidate commit.

| Path | SHA-256 |
| --- | --- |
| `source-tests.log` | `3b8f85226d6488a86a37d9d8f217e8fc08f5bffae68904a8f87cad425548c5da` |
| `license-tests.log` | `3e342e876139aa15624a0fa1fa2aaa80f89d8aef4890998aa6cebc9393aee91d` |
| `staging-tests.log` | `686286104aad8f01aff38d392a34ca5528c5c47d6df5d80f0cd7473978883ca8` |
| `browser-a.log` | `f006040ed031c1b3ce1596c0b75e591bbc87f4d1dcc12217e8e11512718f2c29` |
| `browser-b/summary.json` | `b3ca569da84b86d880130d4d647144f13d181bfa276a939fed9b3d7faf957d5d` |
| `browser-b/source-narrow.png` | `3498a2280c684bf9edc91dde4b08f3a7e2a75938a9c726fb7180ee271c7fcd10` |
| `browser-b/source-unavailable.png` | `debd7e89484d5779277eb96818ecf3c67e51de6fe25635cd812ba8b11bc672c3` |
| `installed/installed-browser-a.log` | `ff4272e3a9bcf85ea3cf7776bcda8e9b9fb642c917b9e2f7649595237ca25327` |
| `installed/installed-browser.log` | `ea912b8c038f79b041d8b485948b20d1ec229e46b385e07f2d1131911f5933e6` |
| `installed/composed-result.json` | `af7571e16836fb297ecdfd319783f1bea8e6c55be909ecbdca766414da51e2ac` |
| `installed/ordinary-source-documents.png` | `41b032dca81905662e74ec7e959fde53972813afd512f587411fe0b94c5f5539` |
| `installed/cleanup.json` | `762a304ed0d2afe8a7b869e97f40ca4a9d142ddf6bb0b9a970d0ec91eac5994f` |
| `installed/retention.json` | `df975a72a3f1c0dbddfbef0e038f6a2e54d6020911c79f2cde3922dc89f7eb2a` |
| `installed/payload-source-hashes.json` | `1086665a4dd1fa18747add59a30d8a6a2973c561246e94454590400ddcbde076` |
