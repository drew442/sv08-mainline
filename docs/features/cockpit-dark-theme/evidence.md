# Cockpit dark theme delivery evidence

## Result and scope

System settings → Appearance now offers Light (default) and Dark. The native labelled select works without administrator access. The browser remembers its choice; no printer setting, hardware draft or runtime service is changed. Shared semantic colors cover host and composed printer surfaces, controls, dialogs, definitions/sources and readable links. Branding and the existing graph palette remain consistent. Headings stay plain; statuses retain icons, text and traffic-light colors.

Acceptance: **preference**, **readability** and **regression** passed. Source file hashes, commands, exit status, attempts and representative screenshot hashes are in [evidence.json](evidence.json). Results bind to these file bytes, rather than claiming a later Git commit was executed. The candidate contains no backend/controller edits.

## Validation

- `standard-final`: 34 theme preference, UI-note and administrator/printer staging tests passed (Node22).
- `theme-final-normal` and `theme-final-zoom`: real installed Chromium, composed factory fixture, keyboard theme choice, reload persistence, retained real dirty draft across theme/session changes, unavailable host feedback, cancelled mode review, no mutation requests and unchanged backing configuration. Normal widths390/1024/1440; genuine profile200% at physical1024/CSS512. Rendered sampled text contrast at least4.5, graph labels/wires and actual failed/armed/complete states checked. This is not comprehensive accessibility certification.
- `base-final`: existing base administrator fixture/browser passed against byte-matching private source copy; equality inputs recorded. Budget protections retained.
- Earlier `printer-1` full composed journey and `config-view-1` ordinary-access configuration journey passed. They predate the narrow storage-read feedback repair; printer/controller/CSS semantics were unchanged after those checks. Final theme, standard and base runs cover the repaired initializer; these earlier results are reuse, not an exact-final-commit rerun.
- Coordinator inspected the complete source/test diff, whitespace checks and semantic Light substitutions. Both stylesheet comparisons preserve previous Light rule values. Author inspected actual postrepair storage warning, hardware, network, failed update, zoom Appearance/review/graph; prior unchanged palette images include390px, Light, amber and green. Coordinator also inspected actual storage/hardware/zoom images.

## Attempts and limitations

All failed attempts remain in the private receipt/log directory. Initial browser failures exposed an ordinary-access-disabled edit and an async readiness race in the test; repaired by authorizing only the actual draft edit and waiting for existing ready state, then testing theme at ordinary access. A whole-storage getter denial exposed existing unhandled host receipt/scheduler reads. Browser fault coverage therefore targets the appearance key; isolated unit execution of the actual appearance initializer also covers global accessor denial. Render review later found dishonest Saved feedback after read denial with successful write; production feedback and asymmetric read/write assertions were corrected and final checks passed.

**Deferred concrete follow-up:** `ui/host/app.js` receipt-history/scheduler localStorage reads (renderJobs and scheduleRefresh) should become fault-safe. Whole Cockpit operation with globally blocked browser storage is not qualified by this feature. Theme-key faults and component initialization are covered; no full-page global-storage pass is claimed.

Disposable RPC/session shims do not qualify live Cockpit PAM, a physical printer, service operation or printing. No printer access, deployment or OS image build was performed. Published fixtures contain synthetic factory state and an OFFLINE TEST banner.

## Execution and publication

One task-scoped named `project_implementer`, explicitly requested medium effort, `fork_turns=none`, owned six UI/test files. It explicitly read the repository sv08-ui-ux skill and relevant references; coordinator did not load the skill body. Effective runtime model/effort were not independently observed. Author self-validation was proportionate to reversible presentation work. No model-quality or savings claim. Coordinator ran disposable checks and owns evidence/records/publication. Cumulative receipts and retained output remain within the900-second/128MiB primary allowance; see JSON. No native goal was replaced.

Representative sanitized visuals: [hardware](visuals/dark-hardware.png), [network](visuals/dark-network.png), [failed update](visuals/dark-update.png). PR publication is for owner review, not deployment.
