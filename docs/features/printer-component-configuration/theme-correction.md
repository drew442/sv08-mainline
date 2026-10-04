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

Installed update and independent review are pending. Scope is only
`/usr/share/cockpit/sv08-printer/{index.html,style.css}`, with exact preimages,
backup, readback and restoration of the read-only root. No service restart,
configuration activation, boot-policy change, heat or motion is required.
