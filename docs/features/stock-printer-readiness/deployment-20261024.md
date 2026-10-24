# PR33 deployment — preparation, awaiting printer access

Owner explicitly set the active native goal to deploy the merged changes using
agents. Deployment source is main633b1a5 (merge d093952; reviewed PR33 code1bde0eb).
This record is preparation evidence, not an installed-success report.

The coordinator's SSH attempts to `sv08@192.168.1.141`,
`sv08@sv08.drewnet.online` and `sv08@192.168.1.150` all returned
`No route to host`. DNS still resolves the printer name to .141; the local
neighbour entries for .141/.150 are FAILED, and sv08.local did not resolve.
No printer state was read or changed. The owner was asked to confirm power/current
address while preparation continued.

A fresh named project_researcher at normal low effort inspected the deployment
source without printer access or changes. Effective runtime settings were not
independently observed. It confirmed that the old UI-only deployment does not
cover PR33: the additive stager refuses differing existing runtime/catalog/unit
bytes, and does not create the observer wanted link. Full host integration creates
`sv08-klipper.service.wants/sv08-calibration-reconcile.service` pointing to
`../sv08-calibration-reconcile.service`; the installed checker requires that link
and runtime hashes. No independent assessment of a concrete live operation has
yet occurred because target facts/preimages are unavailable.

Provisional source payload:67 files,21 compiled/generated Cockpit assets,
39 runtime/service files and7 catalog/dictionary files. It includes the transitive
Python dependency candidates; exact target comparisons must determine the final
compatible update and source/notices inventory before writing. All67 archive
members/hash entries were verified, paths are relative regular files and Python
sources parse. Archive1413120bytes, SHA256
`d3d35f3ee538d15ef0e60446fa97f5fc707fba161b58700988388d0bf13b5e84`.
This provisional archive is not a qualified release or an approved live write.

Private assigned artifacts: `/home/drew/.sv08-pr33-deploy/` contains
`candidate-payload.tar`, `candidate-manifest.json` and `preparation-result.json`.
The source researcher used no experiments. Primary cumulative allowance is
1800process-seconds/512MiB; conservative preparation charge120seconds/4MiB.
Local storage had49GiB free. No images, tool installation or host/printer service
changes were needed.

Next: reach the trusted printer, inspect root/slot/boot identity, idle/stopped
services and disk headroom, record protected hardware/managed configuration
hashes/metadata and prior readiness, inspect exact source preimages/dependencies
and license/source provenance, and prepare an exact rollback. Obtain the required
independent exact-operation assessment before live mutation. Preserve hardware,
calibration and histories; do not invent measurements, bulk-migrate settings or
start printer outputs. Deploy the reviewed complete payload and unit/link with
source-bound manifests; restore root mount mode, check all installed hashes and
six status helpers against prior hardware counts, and observe authenticated
rendering if existing authorized authentication permits. Any absent rendered
acceptance must remain explicit. Native goal remains active and incomplete.
