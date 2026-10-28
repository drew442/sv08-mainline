# Merged PR34/35/37 deployment — 2026-10-28

Owner requested deployment after PR35 and then merged required PR37. Local main fast-forwarded to ffde7e19698ea76f15291ef2efe97ad061bd0459; compatibility feature integrated with unchanged reviewed evidence. All four PR37 CI checks pass. This deployment uses that exact merged source, not an unmerged correction.

Fresh preflight reached sv08@192.168.1.141, healthy nontrial slotB, immutable `/dev/mmcblk2p4`,724MiB root/1.8GiB data free.108recorded project files matched;18unrecorded generated cache files remained. The earlier public-root artifact was a pre-overlay snapshot; the first local comparison correctly refused it. Reconstructing it with the exact hash-verified prior deployment payload matched all108fresh live hashes. No mismatches were waived or hashes refreshed to bless drift.

## Reviewed operation

Prepared13files: composed host index/source.js, finite view/shared provenance runtime,9project license/notice/provenance copies. Seven required replacement; unchanged notices retained.18exact cache preimages were backed up and removed; matching source modules remain. Fixed vendor favicon/logo links and all15protected configuration/state paths were preserved. No other root/runtime/catalogue/unit or boot files were changed.

The named high_consequence_reviewer independently assessed exact script, bundle, plan, source hashes, write/recovery boundary and full-plan rollback. PASS WITH CONDITIONS. It measured all13payload hashes and603source hashes, exact expected109-file inventory and18removals. Profile configured Sol/medium; effective per-turn settings were not separately instrumented. This is an independent operation assessment, not independent live execution or hardware qualification.

Conditions were met: verified uploaded script/bundle hashes and successful live dry run; fresh in-script target/mount/boot/health/no-trial/idle/worker/preimage/parent/vendor/configuration/storage checks; existing shared allocation lock; temporarily quiesced Cockpit and feed timer. Backups and intent journal were fsynced before atomic writes; metadata preserved. Root was restored read-only before ordinary verification/service restoration. The script guards full-plan rollback against external changes and handles partial intents, but abrupt power loss/SIGKILL needs journal reconciliation rather than a blind retry. No rollback was needed or exercised.

## Installed acceptance

[Nonsecret receipt, actual results and artifact hashes](deployment-20261028.json):

- All13payload hashes match; shared validator checks109installed project entries and returns Intact with build ID `557c857c8b8e739bd7c3b576830c635f0de36f11bdbcddc6e3493cffab8e1573`.
- Actual ordinary UID1000 can read the exact three installed public documents. Existing ordinary-account sudo allowlist also passes all seven finite status areas, including provenance. No administrator bridge, password/account change, auth bypass or sudo-policy change.
- Hardware remains revision13,24devices,26definitions,1source,current+previous.15protected paths and boot state retain exact content/ownership/modes. Vendor links unchanged;18specific unrecorded caches absent, no new bytecode from acceptance reads.
- Root remains read-only. Cockpit socket and service active after HTTPS activation; feed timer restored active/enabled. Printer/Moonraker/nginx and observer remain inactive with original masks/enabled state. Existing feed service failed state is unchanged, not relabeled healthy. No printer-service start, configuration publication, recovery activation, firmware, reboot, heater or motion operation.
- Identity status healthy, permanent CA fingerprint unchanged. Actual CA-validated HTTPS200 for FQDN and IP; anonymous login401. Existing SSH trust continued working.

Authenticated owner-browser rendering was not observed. Ordinary live API/file reads, actual HTTPS and source-reviewed PR35 browser/disposable Cockpit results are distinct evidence. Refresh Cockpit to load the new page; no owner credential was obtained to manufacture a browser-session proof.

## Rollback and handoff

Retain `/data/sv08/system/ui-deployments/20261028-pr35-37-ffde7e1/before.tar` (696320bytes), SHA256 `2ab32439cdaaa618504beff50247871bf18633aa31ef9214b112017f254fa517`, adjacent plan/journal/installed-result. Journal deployed. Old PR33 rollback remains untouched. A later restore must recheck target, current afterimages, services, recovery and journal before restoring; do not blindly extract over intervening changes.

Only the two assigned /tmp upload files and their empty directory were removed. Private local artifacts remain in `/home/drew/.sv08-pr35-deploy/resume-20261028/`; no images/tools installed. Primary1200process-seconds/256MiB allowance retained across original attempt, source correction and resume; conservative total charge1000seconds/16MiB, not measured savings or a reset.

This is a development overlay: six unchanged generated environment/layout/feed/policy JSON inputs remain unmatched and source/image qualification stays false. Intact indicates local-record consistency only; no source release, whole-OS authenticity, physical printing or recovery qualification is implied. Previous native source-delivery goal remains complete; no new native goal was created or replaced for deployment.
