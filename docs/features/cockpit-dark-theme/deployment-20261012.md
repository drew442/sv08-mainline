# PR12 dark theme deployment —2026-10-12

Owner requested deployment after merging PR12. Fast-forwarded main to68cf588d8a9db574b25adb6f9f91eae7029c497c; both PR checks passed. Existing composed-panel procedure compiled15 public assets; four changed from installed PR11: host entry page/navigation/style and printer stylesheet. Exact installed PR11 preimages, trusted ownership, root/boot identity, storage and status readiness were checked before atomic replacement (entry page last).

[Installed results and manifest](deployment-20261012.json) pass all15 assets/six status helpers. Hardware remains revision13,24devices,26definitions,1source,current and previous present. Protected configuration bytes/ownership/modes, Python runtime backends, services and boot identity preserved. Root /dev/mmcblk1p4 restored read-only. Cockpit socket active; Klipper/Moonraker/nginx inactive unchanged. No restart, reboot, printer configuration apply or outputs activated.

Rollback: `/data/sv08/system/ui-deployments/20261012-pr12-68cf588/before.tar`. HTTPS returned200 with certificate verification disabled; authenticated installed browser rendering not observed. Source-bound disposable rendered/browser evidence remains separate. Reload Cockpit, then System settings → Appearance → Dark. No administrator access required; choice is browser-local.
