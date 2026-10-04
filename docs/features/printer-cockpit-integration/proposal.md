# Integrate Printer hardware into the Cockpit interface

Date: 2026-10-04. Kind: improvement. Owner correction is in
[owner-request.md](owner-request.md). This amends the previous component feature's
separate-page navigation requirement; its backend, safety and persistence
requirements remain accepted and unchanged.

## Outcome and boundary

One persistent Printer hardware panel inside the selected `sv08-host` document,
with the existing sidebar, branded header and single Cockpit session. Navigation
must feel and behave like Overview, OS images, Software, Host configuration and
Recovery. No second session bar, back-to-host link, nested shell or iframe.
The finite `sv08-printer` asset/helper package remains internal packaging.

Use a canonical `ui/printer/panel.html` composed into the host during staging.
Fixtures use the same composition function. Prefix printer element IDs and scope
its CSS; reuse host styles. Keep host controls isolated from printer controls,
including host polling failure/disable paths. Preserve host notices/image jobs,
but display host-only operation status on host sections rather than above the
printer form. Load one shared existing session adapter; no authentication or
privileged bridge change, dependencies, daemon or upstream edits.

An allowlisted route module handles existing shortcuts/sidebar and hashes for
Overview, images, software, settings, recovery and printer. Direct links,
Back/Forward and refresh work; the old printer URL redirects into this shell.
Keep one mounted controller per section. In-memory dirty selections survive
section changes. Warn before discarding dirty printer edits via explicit reload
or leaving/reloading the document where browser support permits. Navigation and
authority transitions cancel reviews and invalidate delayed responses; never
replay an operation. Reauthorization must not silently overwrite a dirty draft:
explicitly reconcile saved state before mutations. Preserve host dirty settings.

## Delivery and preservation

Implement fresh-root composition and an exact-preimage installed overlay using
the same finite transformation. Historical installed host app.js differs from
HEAD: patch only uniquely matched navigation/control-isolation boundaries and
preserve every unrelated historical host byte. Do not upgrade the host/core or
runtime/helper/catalog/configuration. Preserve originals, modes and ownership;
reject unknown inputs and provide guarded restoration for changed/new files.
A host-only staging/refresh must not publish references to missing printer assets.
Measure payload size; existing storage reserve policies remain unchanged.

Existing private drafts, candidates, prior candidate, backend CAS/generation
checks, thermal protections and service state must be preserved. No configuration
activation, power change, boot-policy change, MCU operation, heat or motion.
Hardware installation is coordinator-owned, preceded by exact-operation review;
existing SSH and retained asset backups provide recovery. Restore root read-only.
No user physical action is required. Deferred commissioning remains deferred.

## Acceptance

- **integration (offline):** one document/header/sidebar/session; active nav state;
  useful inline printer panel with inherited styles; no duplicate IDs/controllers;
  routes/deep-link/reload/history and old URL; dirty printer/host values retained
  across section changes; keyboard focus and responsive 1024×600/desktop/narrow.
- **lifecycle (offline):** shared Stop/logout/disconnect invalidate reviews;
  navigation during review/delayed response cannot revive a stale review; dirty
  reauthorization reconciles explicitly; host status failure cannot disable or
  overwrite printer controls; relevant save/import/export/inactive apply and
  cancel behavior passes. No backend behavior change claimed.
- **staging (offline):** fresh and exact historical composition; expected hashes,
  modes, byte boundaries, missing/unknown preimage refusal, no broken host-only
  staging; guarded restoration and bounded payload; relevant host regression.
- **installed (hardware):** reviewed exact overlay on test-sv08-01, actual
  authenticated shared-shell navigation and dirty-draft retention with read-only
  helper status; route history, legacy URL and responsive screenshots; saved
  configuration/context and service masks unchanged; root/boot read-only and PSU
  off. Installed checks need not save or apply a candidate to establish navigation.

Before evidence: the accepted separate page at `85cb5c7` navigates to another
HTML document and loses the sidebar. Compare source-bound browser captures and
navigation/document identity before/after. Offline evidence is not installed
acceptance or hardware compatibility/release evidence. Independent approval and
independent delivery verification follow the existing feature workflow.
