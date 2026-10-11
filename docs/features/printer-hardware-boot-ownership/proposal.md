# Preserve private hardware state ownership at boot

Installed hardware status refuses revision 13 because boot preparation recursively
assigns application ownership to config/printer-hardware. PrinterStore correctly
requires root-owned 0700 storage and root-owned 0600 files. Retain that protection.
Prepare application files normally but assign this exact managed subtree to root,
including files copied to a new generation. Do not modify saved bytes or fallback.

Acceptance: targeted boot regression proves current/copied hardware subtree is
root-owned, ordinary config remains application-owned, fallback is untouched and
bytes/modes unchanged. Installed metadata repair preserves SHA256 and restores
status with revision13,24devices,26definitions,1source,current/previous present.
Deploy only this reviewed boot module without running it or rebooting.
