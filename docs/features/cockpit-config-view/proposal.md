# View configuration without administrator elevation

Add one fixed root-owned read helper reachable through an exact argument-restricted
NOPASSWD sudo rule. Use isolated Python for the privileged entry point, reject CLI
arguments and unknown/extra JSON fields, allow only explicitly enumerated read
operations, construct child requests instead of forwarding arbitrary input and
sanitize the child environment. No arbitrary paths, modules, commands or mutation
methods. Existing administrator helpers and state modes stay protected. Review
returned status fields; expose public identity/trust/settings, never private keys,
passwords, client-certificate bundles or private backups.

Load all configuration sections on authenticated session availability, independent
of elevation. View navigation, installed component/definition drilldown, connection
filters and network/software selection remain usable. Edits, source changes,
configuration publication, update actions, credential changes, private downloads
and physical/service operations remain gated by elevation in both UI and backend.
Revoke pending reviews on authority changes; keep readable state after End access.
Existing preexisting draft/epoch/session guards remain. Status failures appear as
load errors, never as an empty configuration or a prompt to elevate merely to view.

Acceptance: ordinary authenticated user loads populated hardware/state/source data
and all six settings sections; privileged bridge is not requested for read RPCs;
write/export-secret/unknown-method/extra-field/argument/environment-injection
attempts are refused by the read path; real administrator mutation helpers still
reject ordinary direct invocation; usable view controls coexist with disabled
mutation controls after End access. Staging ships exact helper/sudoers/frontend
closure and metadata. Focused unit/browser/staging checks and source-bound results.
Coordinator obtains independent restricted-root-entry assessment before installing
sudoers and code, then validates actual ordinary-user read/denial on the printer.
No reboot, printer activation, network change or configuration publication.
