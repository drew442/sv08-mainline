# Shared definition icons — 7 October 2026

Owner requested the same icons used on Printer hardware. Source `0089535` extracts one shared category SVG renderer and reuses it on definition, category, component and included-definition cards. Source groups and unknown categories use the existing board icon. Existing text labels remain; icons are decorative, aria-hidden,30px with the same stroke/colour as hardware. No external assets or dependencies.

JavaScript syntax/diff checks and12 staging tests passed. Independently assessed two-file UI overlay installed (app.js/style.css only), with private rollback `/data/sv08/definitions-icons-backup-20261007`. Authenticated installed Chromium checks passed: definition/category SVG paths exactly match hardware; every definition card retains its icon and visible label; source/category/drill-down/history/reload continue to work; responsive widths390/1024/1440 contained; saved hardware state unchanged. Desktop render visually inspected. [Receipt](icons-installed.json).

Post-browser installed/unrelated hashes and saved state/masks/configuration remained unchanged; root/boot RO, data RW, PSU OFF, install unit inactive/MainPID0 and owned tunnel closed. No Save/Apply/output or printer-service action; UI evidence is not physical commissioning.
