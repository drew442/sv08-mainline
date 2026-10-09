# Mainsail access loading-state correction — 2026-10-09

The owner reported an administrator warning and disabled login controls after
selecting Cockpit administrator access. Actual HTTPS Cockpit PAM/sudo sidebar
entry reproduced the misleading warning with `sv08Session.elevated=true` while
its status RPC was pending. The request eventually succeeded: one browser reply
was observed at1802.7ms, and the direct root helper/SSH round trip at2162.7ms.
No backend privilege rejection was observed on this named diagnostic host.

Navigation/privilege invalidation previously always wrote Administrator access is
required. It now chooses the message from actual session authority; refresh also
sets Loading Mainsail access settings before waiting for status. Login controls
remain gated until successful status, then enable automatically. Root authority,
active-page and stale/private-response guards are unchanged. No access policy,
backend, certificates or service configuration changed.

Added a meaningful delayed-reply sidebar and reauthorization case to the existing
mocked Chromium journey. It failed on the old elevated-but-administrator-warning
behavior, then passed with the correction. It verifies loading vs real denial,
controls ready after status, and existing password/no-login/certificate/revoke,
review/cancel, stale responses, privilege/navigation, private-download transport
and narrow-screen behavior. `node --check ui/host/mainsail-access.js`, complete
stable diff and `git diff --check` passed. No unrelated broader testing needed.

The exact single JavaScript asset was atomically installed on diagnostic
`test-sv08-01`, same admitted boot `b1fbaf69-26b9-4f1d-a4e8-369b61ff563f`, PSU OFF.
Existing preimage matched source exactly. The bounded backup/restore operation
preserved34 hashes, physical service masks and no MCU descriptors; root/boot
returned read-only. No service restart, reboot or authentication-mode change.
The correction changes two presentation statements; root/request gates and
installation write boundary are unchanged. It is reversible self-validated
maintenance, without a new consequential authentication transition.
Installed JavaScript SHA256:
`32fbf550e6a2c0165064659a4206e0333b6bc5b32cd13b41834263dc9c6b0b79`.

Actual installed HTTPS Cockpit browser acceptance entered from Overview with
administrator access already granted, observed Loading, waited for ready controls,
selected No login and opened/cancelled review, then verified policy unchanged.
A second sidebar entry also succeeded. No mode was applied to the physical host.
The source/diagnostic work used a bounded300-second primary diagnosis allowance
and existing local browser tools; no child agents or tool installs were needed.
Private-browser cleanup races were isolated to scratch profiles. The final
driver terminates its owned Chrome process group before bounded profile cleanup
and exited zero; the two exact residual profiles from earlier attempts were
removed after verifying no owned browser used them.

This verifies presentation and named web access. It does not claim a permission
failure was observed, or qualify a printing release. Browser sessions need to
reload the page to load the updated asset.
