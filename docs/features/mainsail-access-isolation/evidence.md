# Independent Mainsail access control acceptance — 2026-10-09

Both existing host image-status failure selectors now exempt the independent
Mainsail access page, as they already exempt Printer identity and hardware pages.
The page retains its own root/privilege/health/epoch guard; other host operation
buttons are still disabled on a blocked or failed status read.

Validation: reused the existing mocked Chromium journey with both actual production
failure selectors applied to the DOM. Access Generate/Refresh stayed enabled while
host Save mode became disabled. All three mode, review/cancel, download/revoke,
privilege/navigation and private-response suppression journeys passed. `node
--check ui/host/app.js` and complete two-line diff/`git diff --check` passed.
No new tracked implementation-mirroring test was added for this low-impact change.

Named diagnostic installation used a separately assessed exact one-file operation,
with PSU OFF, the same admitted boot, unchanged password mode, 34 protected path
hashes, production masks and no MCU descriptors. No service restart or reboot.
The installed app is an older accepted variant without later unrelated feed/history
additions; preflight refused full source replacement. Installation instead inserted
only the two exact selector exemptions, retaining every other installed byte.
Input SHA256 `91074643af5032fdd0109064177429df01691822fce08a7c405be00b1d2ed64f`;
output `f913d58ac15f2dc9e4ad4100a2d7c8503fa431fb33d995b7f1ecc3c07cd58c7f`.
The tracked app has the same two narrow additions for future image staging.

Independent operation packet SHA256
`09b04c44a980cfa61b79b16833383a2799b768ffd4c7482416d586f522217f02`;
script `9f5609d97f88b34d2b4e15f96d955ed4ce237bb945951a4dc49a0f7ad42be785`;
passed fixed-role review decision
`8a40092a031143485af6a67ff381e130593785f235a91509cab5ea03621149ef`.
Actual HTTPS Cockpit PAM/sudo opened the installed page, reviewed/cancelled a password
change without changing state, and fit390/1024/1440 widths. Injecting a failure in
the browser's host-status request exercised the actual installed catch handler:
Host unavailable appeared, host buttons disabled, access controls stayed available.
The temporary browser mock was removed; no production backend mutation occurred.

This is self-validated source and independently assessed exact installed web evidence,
not hardware commissioning or release qualification. It does not deploy the unrelated
new feed/history controls to the older diagnostic app. Existing client sessions are
subject to the graceful-reload limitation documented in the primary feature.
