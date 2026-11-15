# PR33 printer deployment — 2026-10-26

Owner restored Beelink access and requested another deployment attempt. Existing
trusted SSH reached `sv08@192.168.1.141`; Wi-Fi .150 remained unavailable. The
printer was on slot B, release `0.1.0-physical-update.2`, immutable root
`/dev/mmcblk2p4`, OS health ready and no trial. Root had725MiB and data1.8GiB free.
All six installed status helpers passed before changes; hardware was revision13,
24devices,26definitions,1source, with current and previous candidates present.
Klipper/Moonraker were runtime-masked, nginx masked, all inactive. Cockpit was
inactive. No pre-existing work or owner configuration was replaced.

## Scope and gate

Deployed source `b74df3a6e39e8983d7748d1d8ff8b742952b4ee3`, containing reviewed
PR33 code `1bde0eb9d82a7a2388b9706bd3c308f028d006b0`. The payload has95files:
compiled/generated UI, catalogue/dictionary, all57current Python modules, the
calibration observer unit, and source/license notices.39files required writes;
unchanged bytes were retained. The exact relative observer wantedlink was added.
The new runtime validated the actual owner's saved configuration in a root-private
volatile staging area before root changes; its summary and15protected
configuration/state paths remained unchanged.

A named default-low source researcher traced payload/dependency/provenance needs.
A separate named high_consequence_reviewer assessed the exact script, plan,
preimages, rollback, complete boot/recovery dependencies and future boot guard.
Initial assessment correctly withheld approval until exact artifacts existed;
final result was PASS WITH CONDITIONS. The configured reviewer profile is
Sol/medium; effective per-turn settings were not independently observed.
Source findings are not a claim of independent live execution verification.

Fresh prechecks met its conditions: exact printer masks/inactive states, no
Mainsail-access transaction (including a symlink), no recovery activation markers,
unchanged boot/target/mount/preimages and pinned Klipper reader/entrypoint/dictionary
hashes. No marker was repaired or deleted. New boot code adds only the existing
read-only activation guard; its dependencies were installed together. No reboot,
boot partition write, recovery activation or configuration publication occurred.

Exact script SHA256
`b34358fc043ae7a5a6f78823755e2e207a700f4b23526d177ef0e4f9111ce270`;
plan `d46ef9c2b9b0010088a5419306a977c665e25b871907d7e34f8248d737d6db83`;
bundle `3ff2ac33548ed57fa6ab6b040b818c9c85712a42a25f115aaa724b5619d0fd59`.
Private artifacts are retained under
`/home/drew/.sv08-pr33-deploy/resumed-20261026/`.

## Installed acceptance

[Nonsecret installed receipt, final audit and payload hashes](deployment-20261026.json)
record actual results:

- All95payload hashes match; all58runtime/service entries and the wantedlink pass
  the installed checker, with trusted ownership and permissions.
- All six status helpers pass. Hardware remains exactly revision13,24devices,
  26definitions,1source,current+previous.15protected paths retain exact bytes and
  ownership/modes; no calibration or definition/history migration was performed.
- Root was restored read-only before service startup and remains read-only.
- Cockpit socket/service are active. Klipper/Moonraker/nginx and the observer
  remain inactive; original printer masks are unchanged. No heater/motion command,
  firmware operation, configuration apply or printer-service start occurred.
- The permanent CA fingerprint is unchanged and identity status is healthy.
  Actual HTTPS returns200 for both FQDN and IP with validation against that CA;
  unauthenticated `/cockpit/login` returns401. Existing SSH trust remained usable.
- Authenticated owner-browser rendering was **not observed**: existing SSH
  authentication did not provide a Cockpit PAM session. No account, password,
  auth policy or session bypass was introduced to facilitate this check. The
  existing PR33 composed-browser/disposable PAM evidence remains separate and
  is not relabelled as owner-session interaction proof.

Cockpit: <https://sv08.drewnet.online:9090/>.

The observer is installed and linked for the normal Klipper lifecycle, but was
not started during deployment. Existing managed configurations need one reviewed
application of the new generated layout before normal native SAVE_CONFIG
reconciliation; deploying code does not silently apply hardware changes or
invent calibration. Configured-printer commissioning remains the recorded
H/session task, and complete recovery qualification still awaits ARM64/KVM.

## Rollback, provenance and cleanup

Exact old software preimages are retained at
`/data/sv08/system/ui-deployments/20261026-pr33-b74df3a/before.tar`,501760bytes,
SHA256 `353f17501a4811e665f3a0cb2215c5c8310ff7ef42a944f54a35fce7b637762a`.
The adjacent plan/journal preserve old ownership/modes, absent/new paths, link
state and protected hashes. Journal phase is deployed. Handled operation errors
would restore checked preimages before returning root read-only; no rollback was
needed or claimed exercised on this printer. Any later rollback must first
recheck current target/source, afterimage hashes, stopped services and receipt;
do not blindly extract an archive or overwrite intervening changes.

Current original-code bytes match published source and AGPL notices were staged.
This is explicitly a development overlay: six retained generated environment,
layout/feed/policy JSON files are unmatched by the generic source recipe. The
provenance reports unqualified source/image status rather than manufacturing a
matching-source or release qualification. No flashable image was built/released.

Only the assigned temporary upload directory was removed. Rollback and nonsecret
receipts remain; no owner backup, private key, password or stored authentication
was inspected or published. No tools were installed. Primary allowance remains
1800process-seconds/512MiB cumulative across the prior network failures and
resume; final conservative charge900seconds/64MiB, with no reset. Source checks
and exact existing PR33 tests/CI were reused where unchanged; no redundant image
or broad test rebuild was needed.
