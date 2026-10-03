# H12 attended SD session preparation — 2026-10-03

Status: **H12 complete.** Full write/flush/readback passed at 05:23 UTC;
normal installed-eMMC slot A boot with SD absent and authenticated SSH passed at
06:32 UTC. Independent completion review passed. Earlier checkpoints below retain
their historical state and do not reopen completed steps.
The [owner's scope](../decisions/20261002-h12-scope-reduction.md) and
[delivery plan](../development/h12-sd-delivery-plan-20261003.md) govern the session.

## Concrete route

Use the already running independent SD host on test printer 01. Its October 2
boot remained reachable on October 3; fresh read-only inspection found the SD
root mounted read-only, eMMC unmounted, no swap and the recovery display service
active. The mainboard revision remains owner-reported H616_JC_6Z_V1.2; these
observations do not qualify stock hardware or printing.

Stage only the reviewed small Python application and its fixed configuration in
volatile storage on this SD system. Keep the root/userspace on SD and read the
full image directly from the independent read-only NFS source. A temporary display
service drop-in selects the attended GTK application. This avoids an unnecessary
SD rewrite/card movement; it is not a RAM-root maintenance handoff. Runtime files
and mounts disappear on restart. Retain the composed SD artifact and exact source
revision for reproducibility and later persistent media preparation if needed.

The existing Beelink export is NFSv3 only. The SD host mounted it successfully with
its installed mount utility and kernel modules, without mount.nfs or new packages:

```sh
mount -i -t nfs -o ro,vers=3,proto=tcp,addr=192.168.1.136,mountaddr=192.168.1.136,mountvers=3,mountproto=tcp,nolock,soft,timeo=20,retrans=2 192.168.1.136:/srv/sv08-sd-nfs /run/h12-source
```

The current mount and file stat are measured evidence. Before confirmation the
application performs its complete source checksum and current device checks.
Network read errors fail the operation; no automatic retry or resume is promised.

## Image and target

- Existing reviewed diagnostic v5 image: 7,818,182,656 bytes; freshly rehashed on
  Beelink as `ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.
- Source visible at `/run/h12-source/image.bin` on the read-only NFS mount.
- Intended spare eMMC: measured whole MMC user area on controller `4022000.mmc`,
  31,272,730,624 bytes. Exact current CID, resolved controller path and dev_t stay
  in ignored session evidence/configuration and must match the opened descriptor.
- The image replaces its complete range, including contained user data and boot
  environment. Storage beyond that range and eMMC boot partitions are excluded.
- This image previously reached installed Debian/SSH. Its known Cockpit/boot-health
  limitations remain; H12 acceptance is normal installed-system boot, not a printing
  system or complete host-product qualification.

## Remaining operation sequence

1. Complete installed ARM64 execution and independent software verification.
2. Bind the exact accepted application hashes, image and fresh target identity to
   the physical operation record; prepare display invocation and result capture.
3. Confirm current PSU/USB/media setup, no new irreplaceable data on the spare,
   and owner attendance. Obtain exact high-consequence review before enabling the
   destructive operation. Existing scoped authority is retained; the owner supplies
   the affirmative Yes for this image/target through the attended interface.
4. Review image/target; No or no answer performs no write. After Yes, keep power
   and source access through write, flush and full image-range readback.
5. Report actual result. On success, give the operator the concrete manual
   restart/SD-removal instruction and observe installed root/access. On failure,
   retain SD recovery and evidence. Never reboot automatically.

No separate rehearsal boot, permission claims, randomness, expiry, cold capture,
factory restore trial, MCU operation, heater or motion is part of this session.
Physical setup/attendance is not inferred from SSH reachability. H12 remains open
until the actual write/readback and manually restarted normal boot are observed.

## Attended authorization and exact review

At 03:19 UTC the owner confirmed PSU off, USB host power, Ethernet, installed SD
and spare eMMC, no irreplaceable spare data and attendance. Keyboard/mouse input
woke the physical HDMI recovery menu. KVM capture still reports no HDMI signal;
physical visibility is owner-reported and KVM capture is not established.
Fresh read-only inspection matched the prepared spare identity, the same SD boot,
read-only source and unused eMMC. Stored factory media is not a new gate.

Separate `high_consequence_reviewer` session
`01a0ffc7-7fd0-7b13-be2f-bcfec9f13f60` returned **PASS WITH CONDITIONS** for
volatile application/configuration staging, this exact image-range write after
owner Yes, and the subsequent manual restart. Actual GPT-6.1 Sol/medium,
full-access/never and complete role instructions were verified from session
metadata. Exact review and prepared hashes are preserved in ignored session
records; unique media identifiers remain private. No uncertainty required a
higher-tier review. This review is recorded before deployment/enablement.

Conditions: read back deployed file hashes and retain the measured boot/source/
target/recovery gate; verify effective display ExecStart and Restart=no; owner
must see readable image/target/destructive text after integrated full client hash
and select Yes themselves. Preserve power/Ethernet/source through transfer. Stop
on error, changed facts or ambiguous result, without retry/reboot. Capture matched
write/flush/full-readback screen result, process and block-I/O evidence before
manual restart. Then observe new boot ID and installed root/SSH. SD remains the
fallback. No physical write or success is established by this approval.

## Native screen enabled

At 03:25 UTC coordinator staged the exact reviewed files in `/run`, read back
all five matching SHA-256 hashes, and restarted only the display service.
Effective ExecStart selects the reviewed `/run/sv08/h12/sv08_sd_reimage_ui.py`;
Restart=no, service active and boot ID unchanged were measured. An actual Gdk
capture shows the readable 1024×600 initial screen with Review and Refresh.
The owner’s physical visibility report preceded this screen change; KVM capture
remains unverified. Initial eMMC block statistics recorded zero completed writes
and zero written sectors on this boot. No Review/Yes was selected by coordinator.

Next owner action: use Review image and target; allow integrated complete image
checking. On a readable confirmation for the prepared source and intended spare,
owner may select Yes to begin. Keep power/source connected and report the result;
do not restart until success evidence has been retained. Exact write/flush/readback
and normal boot are still unachieved at this checkpoint.

## KVM return and keyboard correction

The owner reported that Enter chose No, Tab did not visibly change the selection,
and the selected answer was unclear. After rebooting, bypassing the HDMI splitter
and updating GLKVM EDID, the owner requested an autonomous retry through KVM.
This delegates operation of the confirmation to the coordinator under the existing
identified-image/spare-eMMC authority; it supersedes the earlier owner-alone keypress
instruction for this retry. The owner last confirmed PSU off, USB host power,
Ethernet, SD and spare installed and no irreplaceable spare data. Only the reboot
and video-chain changes were subsequently reported.

On the new SD boot, actual KVM video and discrete press/release keystrokes work.
The original UI passed a disposable-file Tab/Enter journey after those changes,
so the prior physical failure has no uniquely established cause. A separate local
X test reproduced missing native focus. The correction explicitly presents the
window/dialog and adds a thick selected-button outline and a textual selected
answer. No remains the default; no backend/write policy changes were made.

The old GTK driver programmatically focused Yes and did not establish native Tab
navigation. Its historical passing result is preserved with that limitation.
The replacement uses actual key events and checks native focus, Tab/Shift+Tab,
No/Yes/Escape/close/absent answer, failure refusal and resulting file bytes.
An initial installed run failed by sampling focus too early. The corrected driver
waits within the existing ten-second deadline, preserves timed focus evidence and
still fails when focus never arrives. All ten cases now pass on the installed
ARM64 SD desktop; measured dialog focus arrived after roughly half a second.
Real GLKVM Enter-on-No left the disposable file unchanged, and Tab then Enter-on-Yes
wrote and read back that file. Readable KVM screenshots show both selected answers.
These are file fixtures, not an eMMC write or hardware durability qualification.

Correction candidate: `ba40c0c`, based on `282ddca`. Runtime UI SHA-256:
`b34e6010b3de50ff8cd82b662eef815c35ad39eb6ce6664940543defcf811ae4`.
Backend remains
`a75aad51d6bc01aa2cf527cfa4f1f600ee61189a265d13ef0979eeeab448b304`.
The current SD root remains read-only, the same intended spare is unmounted with
no swap, and its measured completed writes/written sectors remain zero. The
read-only NFS source is remounted. Exact identities, screenshots, fixture receipts,
failed runs and review packets are retained in ignored session evidence.
This correction is tested in the installed SD userspace via temporary runtime
files; no newly composed SD image is claimed. Fresh software and action reviews
must pass before production deployment/confirmation on this new boot.

### Fresh independent reviews before production enablement

Correction delivery verifier `01a1001b-6283-75f2-a9c7-5c1b60e89eba` passed the
complete candidate diff and evidence, including an independent before/after Xvfb
reproduction. Its formal result retains its own launch uncertainty; coordinator
inspection separately confirmed actual GPT-6.1 Sol/medium, full role loaded and
full-access/never. The [correction evidence](../features/h12-attended-sd-reimage/keyboard-correction-evidence.json)
and [formal verification](../features/h12-attended-sd-reimage/keyboard-correction-verification.json)
preserve the result and limits.

Fresh high-consequence reviewer `01a1001b-66fb-7d83-827f-f8d9446810e4` returned
PASS WITH CONDITIONS for the new boot, unchanged backend/image/target and corrected
UI. Actual Sol 6.1/medium and complete role were verified. Both reviewers ran as
separate full-role CLI sessions because native agent capacity was unavailable.
The action review explicitly permits coordinator KVM confirmation under the
owner's existing flashing authority and latest autonomous-retry delegation.

Before enablement, verify staged hashes, exact configuration, boot, target,
capacity, independent recovery marker and effective production entry point with
Restart=no. Complete native source hashing and inspect the actual confirmation;
then Tab, inspect visible Yes, then Enter with each key released. Stop on mismatch,
refusal or ambiguity. Preserve power/source during transfer, record matched result
and terminal writer before manual restart; observe installed root and SSH after it.
These reviews are recorded before production enablement; neither claims execution.

### Corrected production screen enabled and Review started

At 04:56–04:57 UTC the coordinator deployed and read back the accepted backend,
UI and exact configuration hashes, verified the same current boot/target/capacity
and recovery marker, and restarted only the display service. Effective ExecStart
uses the production UI/installed_session, with Restart=no; the prior disposable
fixture entry point is no longer selected. Actual KVM capture showed the initial
screen. A released Enter opened Review at 04:57:03 UTC; KVM then showed image/target
checking. Source hashing is in progress. Target writes remain zero. No Yes or
physical success is claimed at this checkpoint.

### Confirmation accepted; physical write started

The full client image check completed by 05:08 UTC. The X server's default
600-second DPMS timeout blanked HDMI during checking; measured X state was
Monitor Off. Coordinator woke the display and disabled DPMS/screensaver for this
session using installed xset. KVM video returned. This is a session setting;
persistent display policy is not claimed fixed.

Actual KVM confirmation showed the accepted image size/SHA, intended spare
controller/CID/dev_t and complete replacement warning, with No visibly selected.
One released Tab visibly selected Yes. Under the recorded delegation, coordinator
sent released Enter at 05:09:57 UTC. KVM then showed Writing and verifying; keep
power on. Target write counters began increasing. Transfer/readback is in progress;
no success or permission to disconnect/restart is claimed at this checkpoint.

### Physical write and complete readback passed

By 05:23:26 UTC, actual KVM video displayed **Complete image-range write, flush
and readback matched**. The unchanged reviewed backend reaches that message only
after transferred-source hashing, fsync, block-cache flush and full image-range
readback hashing all pass. The source SHA remains
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.
Measured target writes total 15,269,888 sectors of 512 bytes, exactly
7,818,182,656 bytes, and process write_bytes agrees. No target I/O is in flight.
The UI process remains alive at its terminal result with source and target
file descriptors closed. Final runtime/configuration hashes still match review;
root remains the independent read-only SD. Evidence is summarized in the
[physical receipt](../features/h12-attended-sd-reimage/physical-write-evidence.json).

The remaining owner step is now concrete: keep PSU off; disconnect USB host
power; remove SD while unpowered, leaving spare eMMC installed; reconnect USB
with Ethernet/KVM connected. Coordinator will observe a new boot, installed root
and SSH. If normal boot fails, retain SD for unpowered reinsertion/recovery.
The manual restart has been requested but is not yet observed. H12 remains open
for that final check. This outcome is not printer/MCU/heater/motion qualification.

### Subsequent restart and USB relay — 06:17 UTC

Owner reported the requested restart and an HW-667 NC-wired USB power relay.
The [independently reviewed relay test](host-hw667-test-20261003.md) successfully
power-cycled the host and restored SSH/KVM. Both before and after that test, Linux
identified the 16 GB SD as the running root and the accepted spare MMC as unused.
The SD-removal discrepancy is pending owner clarification. Normal eMMC boot has
not yet been tested by these observed boots; the complete write/readback result
remains valid. Do not infer failed eMMC boot from this SD recovery screen.

### Final eMMC-only boot and independent completion

After the owner removed SD and requested relay control, fresh action review
`01a10074-58c1-7a51-a304-1141daa7fe92` passed. The exact tested HW-667 script
cut USB power at 06:30:50 UTC and restored it at 06:30:55. Authenticated SSH then
measured a new boot ID, accepted spare MMC CID/controller, read-only root-a,
slot A, writable /data and no SD device. KVM showed Debian 13 sv08 login.
No units were failed at that observation; historical diagnostic limitations are
not declared repaired. The [completion record](../features/h12-attended-sd-reimage/physical-completion.md)
and boot receipt retain evidence and limits.

Separate verifier session `01a10078-b5ad-79d0-a8cc-6f32125c9780` passed both
physical preparation and completed-write/normal-boot acceptance. Coordinator
verified actual GPT-6.1 Sol/medium, full-role loading and independent provenance.
Formal results are imported into the feature record. No further reset or owner
action is needed. Use HW-667 for future authorized power resets; coordinate media
moves with relay power held off. No automatic maintenance return was introduced.
