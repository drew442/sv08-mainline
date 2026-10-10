# Cockpit context: retrieve only the affected contracts

The web interface is the existing host administration package, not the printer's
ordinary printing UI. Start with `ui/host/` and the named handler/test. Reuse its
HTML, JavaScript, CSS, components and supported Cockpit bridge; do not introduce
React, PatternFly, Playwright or a build system just to follow a generic design recipe.

[Decision 0010](../../../../docs/decisions/0010-host-administration-and-recovery-ui.md)
requires ordinary OS administration without Linux commands and preserves the finite
status → review → apply contract. A refresh or page load must not install, reboot,
change mode or declare a release healthy. Selection, staging, applying and rebooting
are different operations. Explain disabled operations and next steps honestly.
Keep authentication, stale-review checks, idle admission, recovery and data
protections in the backend; understandable wording does not replace those controls.

For the integrated hardware panel, start with `ui/printer/panel.html` and
`scripts/stage_printer_ui.py:compose_host`, not a separate host shell. Preserve
the [shared-panel invariants](../../../../docs/development/printer-cockpit-panel.md)
and its feature-specific browser fixture. For printer hardware pages, consult the accepted
[page design](../../../../docs/development/printer-hardware-page-design.md) and,
only when sources/imports are involved,
[definition-source design](../../../../docs/development/printer-definition-sources-design.md).
Use recognizable component sections and labeled outline icons, not decorative
hardware photographs/renders. Keep Components, Connections and Changes task-led.
Distinguish available definitions, selected hardware, reviewed changes and applied
configuration. Third-party repositories supply version-pinned, reviewable data,
not executable plugins or permission to mutate the printer. Preserve local overrides
and offline behavior. Do not rewrite those requirements into another competing spec.

[UI evidence and fixture commands](../../../../docs/hardware/host-admin-ui.md)
describe the loopback test bridge and its limits. It exercises disposable controller
state, not production Cockpit authentication, assembled images or real hardware.
For installed session/elevation changes, follow the applicable existing
[Cockpit checks](../../../../docs/hardware/host-admin-cockpit.md). GTK recovery is a
separate native interface: a web fixture cannot establish its acceptance.
