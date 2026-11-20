# Supported configured-printer candidate build

This is the supported candidate extension of the existing host/recovery builders.
It does not declare a printing release. Use [the release contract](../remaining-work-plan.md)
and [the commissioning session](../hardware/test-sv08-01-commissioning-session.md).
Diagnostic commands retain their masks and `deployable:false` rejection contract.
A supported manifest's `deployable:true` selects the actual backend; its receipts
still say `printing_qualified:false` and `release_qualified:false`.

## Inputs and boundaries

Freeze clean committed source. Build an explicit profile against
[profile.schema.json](../../configs/host-os/supported/profile.schema.json).
The current profile is intentionally limited to test-sv08-01: its reviewed board
artifacts, six GPT identities, U-Boot index and measured CID. The CID digest is
a physical binding, not an owner credential. Recheck the actual medium before
installation. A different printer requires its own measured inputs and qualification;
do not publish an image as generic stock hardware support. Fitted bed/hotend/sensors
are selected through definitions after installation, independently of this host profile.

Use the pinned host Klipper revision. Integration snapshots the release's immutable
MCU recommendations from definitions. Installed MCU identity/revision and measured
compatibility remain separate evidence. No builder, owner setup or boot permission
flashes an MCU; rollback may require explicit maintenance and compatibility review.

Supply a **public PEM release authority certificate**, never a private key. It is
the signed-update trust anchor. Optional `feed` declares a fixed HTTPS directory
and channel for LAN discovery. TLS and signed discovery use that explicit CA;
issue a separate TLS leaf for the actual LAN source's SANs. With no feed, signed
manual LAN bundle upload remains available and the fixed feed service is skipped.
Do not replace HTTPS/signature verification with an insecure transport exception.

The root must come from real completed profile/bootstrap/package/refresh stages,
with current pinned apps, board packages and RAUC. Reuse measured package bytes
only when relevant inputs match. Public roots contain locked root/sv08 accounts,
no inherited owner key/password, no machine/host identity or network credentials,
and empty data. Do not promote the historical commissioning overlay, private
qualification shadow, test markers or fabricated OS-health marker.

## Existing composition stages

Assign `$REPO` and fresh paths below its `build/` in a private execution environment.
Check storage/inodes and record process/output ceilings before bootstrap/assembly.
Use [the baseline recipe](../hardware/host-ab-build.md), pinned package tools and
[release packaging](release-packaging.md); full images do not belong in Git.

1. Render the manifest with `supported_candidate.profile_check(profile)`. Stage
   through `integrate_host_os.py --supported-profile PROFILE --release-certificate
   PUBLIC_PEM --manifest MANIFEST --work WORK --execute`. No owner-key argument is
   allowed in supported mode. The builder installs production backend documents,
   real OS health, the explicit commissioning guard and the supported guarded
   boot activation helper; physical units remain disabled and package aliases masked.
2. Use existing printer/admin staging and public-source/notice qualification at
   the frozen revision. Supported backend documents have deterministic recipes,
   and profile/certificate bytes are separately bounded/hash-bound build inputs.
   Unknown or changed bytes remain unqualified. Package notice/source obligations
   remain mandatory beyond project-only provenance.
3. Run `finalize_supported_host.py --work WORK --data EMPTY_DATA --profile PROFILE
   --execute`. It checks fresh stage receipts, public account hygiene, exact
   backend/current service bindings, actual initramfs identity hook and source
   provenance. Source must be clean and match the profile.
4. Build current recovery with the existing `recovery_image.py` stages and exact
   board profile. Its component manifest retains the normal release identity,
   revision, source and MCU assignment, sets `component: "independent-recovery"`
   and `deployable: false`: recovery is not a normal A/B host. The normal manifest
   remains `deployable: true`. Pass this recovery manifest and reviewed target policy;
   source/runtime/notice bindings must be current. Assemble eMMC with
   `assemble_supported_candidate.py --host WORK --recovery RECOVERY --data EMPTY_DATA
   --spl SPL --spl-record SPL_RECORD --profile PROFILE --work OUTPUT --execute`.
   This reuses the existing six-partition builder, GPT/SPL bounds, fsck and input
   preservation checks. Keep artifact hashes and realistic factory-capacity
   filesystem/staging/state-copy/inode measurements.

## Independent SD owner setup

Recovery restore deliberately refuses a target on its own physical disk. Preserve
that fence. Initial setup and password reset use an **independent SD recovery**,
not writable data on the recovery root's own eMMC disk.

Derive/build current recovery using
[recovery-sd.json](../../configs/host-os/supported/recovery-sd.json), the same pinned
board packages and an independently reviewed `--restore-profile`. Its index-2
PARTUUID/filesystem UUID differ from installed eMMC recovery. The policy must
identify the actual SD and eMMC data target; no guessed inventory or automatic
normal-boot enrollment is supported.

Prepare payloads with `assemble_supported_candidate.py --medium sd-payloads
--recovery RECOVERY --work SD_PAYLOADS --execute`. This verifies current source,
recovery receipts and exact Image/DTB before creating the script and environment.
Compile the SD-only loader against that script/environment using the existing
[SD loader recipe](../hardware/host-sd-recovery-host.md), then use its existing
`build_sd_recovery_host.py assemble` command on these payloads. The admitted loader
must bind their exact hashes, disable persistent environment/RAUC writes and boot
SD only. The old recovery userspace/source hash is **not** reused or promoted.

Installation still uses the reviewed H12 source/hash/target/write/readback route
and manual restart. Current SD preparation does not add automatic recovery return.
After verified installation and refreshed partition inventory, the local owner
chooses **Create fresh state → Set owner password (Fresh state) → Use fresh state**,
reviews each change, then performs the documented manual return to normal boot.
See [owner setup](owner-setup.md) for reset, cancellation and persistence semantics.
Actual SD boot, display/touch and this whole journey need candidate-specific evidence.

## Service startup and acceptance

Hardware publication leaves services stopped. The supported Klipper unit checks
`sv08_commissioning.py check` in addition to existing health/trial/shutdown guards.
A root coordinator can inspect `review`, then record `authorize --review-sha256 HASH
--assessment REFERENCE` only after the exact physical-operation authority/review.
This writes permission and performs no service operation. It binds the managed
publication, fitted hardware binding and host/MCU recommendation. Native
`SAVE_CONFIG` remains under the existing recognized calibration lane and does not
invalidate permission. New hardware publication or host pin requires a new review.
On later boots, `sv08-commissioned-start.service` runs only after successful
`sv08-prepare.service` and real `sv08-boot-health.service`. It checks the full
persistent permission under state/shutdown admission locks, releases the locks,
then queues `sv08-klipper.service` with `systemctl --no-block start`. Klipper keeps
its own configuration, trial, health, shutdown and commissioning checks at actual
execution. Missing, revoked, stale or inadmissible permission queues nothing and
logs the reason in the helper's journal. The helper never enables a physical unit
or starts a second Moonraker; the enabled printer API already supplies Moonraker.
Valid permission survives compatible host updates, A/B selection and both root
modes without a writable-root enable operation. Unconfirmed trial boots remain
stopped. After real OS health durably confirms the matching update transaction,
the health coordinator atomically publishes `boot.json` with `trial: false` before
clearing the trial marker and publishing OS readiness. Retained valid permission
can then start Klipper in that same boot, without another reboot or manual Linux
work. Metadata publication failure leaves readiness closed and the trial gate
retained. Recording permission still performs no service action; the first start
remains in the reviewed packet.
The exact launch/stop operations belong in the attended packet, not a generic
unmask/start instruction. Permission is not measured MCU compatibility or printing
acceptance. No user needs to fabricate health files.

Source fixtures and Xvfb render tests are distinct from installed native PAM,
factory-capacity artifacts, physical peripherals, commissioning/printing, signed
LAN update/fallback and independent recovery qualification. Complete those phases
and public source/notices before publishing a supported release.

Recovery `intake` and `assemble` now default to the additive
[`recovery-owner-packages.json`](../../configs/host-os/supported/recovery-owner-packages.json)
supplement. It supplies the pinned OpenSSL CLI used by owner password hashing;
the historical base recovery package lock remains unchanged. Reuse base archives
whose locked size and SHA-256 still match, and intake the additional archive before
a fresh assembly. `--package-supplement PATH` selects an explicit compatible
supplement; it has no effect on derive/build. Supplements cannot replace base
packages or resolve dependencies/upgrades. Intake and assembly receipts bind its
exact bytes and refuse changes during execution.

A root with the owner helper but no `/usr/bin/openssl` is refused before image
compression/allocation. Reassemble with the default supplement, then derive/build
from that fresh assembly. This dependency check and offline fixtures do not prove
native PAM authentication or a physical owner-setup journey.
