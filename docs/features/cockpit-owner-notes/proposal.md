# Cockpit owner notes

Implement the owner notes in the existing shell, outline icon system and frontend. Section navigation and object/device representations receive icons; h1–h6 headings remain undecorated. Retain backend operations, authority gates, configuration and calibration.

Acceptance before editing:
- network-filter: loopback excluded from visible cards/options/reconnect addresses; unused p2p-dev-wlan* excluded while actually active P2P remains visible, ordinary Ethernet/WiFi retained, refreshed missing selection cannot mutate a hidden target.
- update-status: terminal failure/failed health overrides historical reboot-queued feed copy and green presentation; successful, pending/action-required and unknown states remain distinct, with textual/icon semantics and appropriate red/amber/green or neutral tone. No replay/automatic remediation.
- presentation: all section navigation and object/device representations use labelled outline icons without icons on h1–h6; status meanings use icons/text as well as traffic-light colour; default Connections graph while retaining explicit list selection and keyboard access; neighbouring buttons have visible spacing at supported widths/200% zoom.
- regression: deterministic unit and real Chromium composed-panel/host/network journeys, ordinary access/drafts/review/cancel/error/no unintended mutations, representative rendered evidence actually inspected, source-bound hashes and standard staging checks. Fixture evidence is not physical/PAM qualification.

Primary execution allowance2400 cumulative process-seconds/256MiB outputs; one installed Node22/Chromium, local loopback fixtures, no OS images/install/network hardware or printer. Incidental worker limits remain2 experiments/300seconds/256MiB across handoffs. Two children/one implementation. No routine independent review for reversible self-validated UI. Publish owner-review PR; no merge/deploy.
