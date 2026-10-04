# Printer hardware theme correction — 2026-10-04

Owner requested that Printer hardware match the existing Cockpit SV08 Mainline
branding. This is a visual correction within the accepted feature, with no new
configuration operations. The original page forced an unrelated dark palette.

The corrected page uses the Host administration navy SV08 MAINLINE header, teal
accents, light background, white cards, typography, session controls and dialogs.
The local stylesheet keeps the package independently installable. Its shared
visual baseline comes from `ui/host/style.css`; keep the two aligned until a
shared packaged theme replaces these local styles. Existing scripts, identifiers,
configuration operations and authentication remain unchanged.

Offline Chromium checks cover 1440×900, 1024×600 and 390×844, palette/branding,
no horizontal overflow, keyboard Tab focus and dialog Escape cancellation.
Screenshots were visually inspected. The broader existing browser journey exposed
an asynchronous apply-wait failure; it is not claimed as passing for this change.
The visual harness first requested the already-selected board (no dialog expected);
correcting its fixture selection passed. Initial fixture launches also refused
writable repository ancestry; the successful fixture uses a private cache directory.

Installed update and independent review passed. Scope was only
`/usr/share/cockpit/sv08-printer/{index.html,style.css}`, with exact preimages,
backup, readback and restoration of the read-only root. No service restart,
configuration activation, boot-policy change, heat or motion is required.


## Installed acceptance

Source candidate `69d660b8844d777776a402dd744d49759d12fb06` is installed on
test-sv08-01. The exact two-file update passed its dry run, separate action review,
backup and hash readback. Root and boot are read-only; boot identity, saved
configuration and generation context are unchanged. Printer services remain
masked and inactive. PSU was confirmed OFF immediately before installation.
No restart or physical commissioning was performed.

Actual authenticated Cockpit checks passed at 1440×900, 1024×600 and 390×844:
matching header/palette, no horizontal overflow and unchanged saved state.
The browser logged out afterward. Desktop and printer-screen captures were
visually inspected. Private screenshots and original files are retained locally.

The first software review rejected missing source/evidence binding; the corrected
run records and checks source hashes before and after capture. The independent
review then passed. Native agent slots were exhausted, so separate full-role CLI
sessions used verified GPT-6.1 Sol/medium, full access, and disabled delegation.
The verifier's two independent browser probes failed in its harness and are
preserved; acceptance uses inspected coordinator evidence, not a claimed
independent browser execution.

- [Offline visual receipt](evidence/theme/offline.json)
- [Installed browser receipt](evidence/theme/installed.json)
- [Post-installation checks](evidence/theme/postcheck.json)
- [Initial software review](reviews/20261004-theme-software-initial.json)
- [Final software review](reviews/20261004-theme-software-final.json)
- [Exact-operation review](reviews/20261004-theme-action.md)
- [Installed delivery review](reviews/20261004-theme-installed.json)
