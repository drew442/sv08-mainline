# Cockpit task-focused UI/UX delivery

Implement W0–W8 in [the workplan](../../development/cockpit-ui-ux-workplan.md)
under [owner authorization](owner-request.md). Preserve core functionality and
backend authorization, review freshness, admission, update trust/integrity,
recovery, secrets and reconciliation. UI navigation, labels, presentation and
interaction sequences may change. Self-validation applies to reversible source
and disposable browser work; no hardware operation or identity restore is included.

W0 selects six main destinations: Overview, Hardware, Updates, Network,
Access & identity, System & recovery. Legacy hashes remain contextual routes.
Hardware provides Parts, Definitions, Sources and Connections; connection tables
lead signal lookup, with the graph retained for tracing. Access includes login
and identity; System includes mode, software and recovery. Useful deep links,
single-session semantics and unfinished draft continuity remain supported.

The main hardware journey selects parts, reviews a generated inactive candidate,
then explicitly reviews/applies service effects through existing backend operations.
Intermediate saved state is explained; incomplete draft save, standalone generation,
export, import, history, migration, reconciliation, calibrations and overrides remain
available as secondary tasks. No selection triggers live application or calibration.
Catalogue/source tasks return to the invoking component. Updates leads with running
and fallback state and automatic preference; manual operations show their stage.
Access/identity distinguish Mainsail control, client certificates, printer CA trust
and SSH/identity backups. Network rollback and reconnect remain explicit.

Acceptance comprises all applicable W0–W8 checks: trustworthy typed status,
responsive task shell, coherent hardware journey, integrated catalogue, updates
and software guidance, successful/failing service states, keyboard/focus/dialogs,
200% zoom and refresh call-count evidence. Use existing browser/controller suites,
inspect rendered evidence and report offline/installed limits. Source-only service
RPC fixtures cannot prove installed authentication. No CPU savings are inferred.
