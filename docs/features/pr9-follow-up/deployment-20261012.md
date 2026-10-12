# PR10 printer UI deployment —2026-10-12

Owner requested deployment after merging PR10. Fast-forwarded local main and deployed merged source `b9d61db91bc81fddb643a825daf6920235f596f2` to `sv08@192.168.1.141`. [Exact hashes and installed results](deployment-20261012.json) bind all15 public assets, including the composed host HTML and matching printer panel.

The coordinator rechecked exact installed preimages, trusted parent ownership, boot/root identity, hardware summary, protected configuration hashes/modes, backend hashes and service states before writing. Public rollback copies remain at `/data/sv08/system/ui-deployments/20261012-pr10-b9d61db/before.tar`. Replacement used atomic per-file writes and placed the host entry page last. The installed functional checker passed every asset and all six status areas; saved hardware remains revision13,24 devices,26 definitions,1 source, with current and previous configurations available. Protected hardware/managed bytes and metadata and installed Python backends are unchanged.

Root `/dev/mmcblk1p4` is restored read-only, boot identity unchanged. Cockpit socket remains active; Klipper, Moonraker and nginx remain inactive. No backend/service configuration, printer configuration, credential, boot slot, recovery media, heater/motion activation, restart or reboot was performed.

HTTPS returned200 with TLS trust verification disabled. Authenticated rendering on the physical printer was not observed in this deployment; source-matched disposable Cockpit/PAM browser evidence is separate. Installed asset hashes and populated functional results establish deployment and backend readiness, not physical browser usability or certificate-trust qualification. Reload Cockpit to fetch the updated static assets.
