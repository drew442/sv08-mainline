FAIL — deadline-only repair and continuation

Packet SHA256: 3ae3f93863d277e5a80760d4f6e2b53996aeac62f29032902cd4b594ab36c088

1. Existing measured847721f2 startup failure occupies the production boot-failure filename. record_failure refuses a later HostHealth record on that same boot before fallback. The two-leaf deadline fix cannot perform the requested first failed-health reboot. Preserve original diagnostics and correct distinct startup/health failure handling; independently assess exact changed inputs before retry.

2. Packet patches /usr health unit, while original public A/B roots contain regular /etc health units that take precedence. Installed intake does not show actual FragmentPath or /etc identity. Measure both slots and repair the controlling unit path; require effective95s ceiling after daemon reload before health.

The proposed deadline math itself is bounded and preserves40s polling/fixture180. Producer31-test result passes, but the observed delivery/continuation defects remain. No hardware action performed. Prior review missed the duplicate diagnostic-name interaction and is corrected by this source-plus-measured finding.
