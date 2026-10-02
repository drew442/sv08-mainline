# Branch archive — 2026-10-02

The owner requested cleanup of merged, abandoned and deferred branches. Annotated
`archive/20261002/` tags preserve every removed branch tip, including distinct
local/GitHub variants. These are archive tags, not release tags. No commit history
was rewritten. Branch cleanup does not remove implementation from main, change
historical acceptance results, or make incomplete physical work complete.

Classification: `merged` means the exact tip was an ancestor of main at cleanup;
`superseded` preserves an earlier candidate or policy-backport tip without claiming
it was merged. `abandoned` and `deferred` follow the
[owner’s H12 decision](../decisions/20261002-h12-scope-reduction.md).
Automated recovery-handoff branches are deferred; permission-security and separate
RAM-preflight branches are abandoned. Useful historical source remains recoverable.

The remaining working branches are `main` and `wip/host-image-job-resolution`.
The latter preserves a worktree with uncommitted tracked and untracked files;
those files were not committed, removed or treated as accepted delivery. Clean
archived worktrees remain on disk at their original commits with detached HEADs.
Historical feature records may name removed branches; their exact commit IDs and
archive tags remain valid. Future work starts a new branch from main, or from an
archive tag when deliberately resuming deferred work. For example:
`git switch -c feature/resumed-work <archive-tag>`.

The earlier temporary `backup/local-20261002/` branches are also replaced by tags.
Tags are pushed and verified before branch deletion; branch removal is guarded
against changes to the observed GitHub tips.

## Preserved tips

| Original branch | Status | Commit | Archive tag |
| --- | --- | --- | --- |
| `codex/gpt-6-1-sol-routing-pilot` | merged | `77d44224fc6ca35459d8753f38dcd9113024f22d` | `archive/20261002/merged/codex/gpt-6-1-sol-routing-pilot` |
| `codex/role-preserving-yolo-diagnostics` | merged | `ce451fd625f8f96c8b63be9be36c5780df09fb6c` | `archive/20261002/merged/codex/role-preserving-yolo-diagnostics` |
| `feature/h10-network-probe-correction` | merged | `2b51bbfb26d2a33aba21597e5bf63797cfef4a7b` | `archive/20261002/merged/feature/h10-network-probe-correction` |
| `feature/h616-claim-startup-readiness` | abandoned | `0708a18a2528929ad9a59c22e32d865003e95ed2` | `archive/20261002/abandoned/feature/h616-claim-startup-readiness` |
| `feature/h616-emmc-node-binding` | superseded | `a1854e25e5164cb6a462c541b8d1bbe7043994ba` | `archive/20261002/superseded/feature/h616-emmc-node-binding` |
| `feature/h616-emmc-node-binding-marker-repair` | merged | `9d98550d91eb3396f6debd0ee5e03196530c0723` | `archive/20261002/merged/feature/h616-emmc-node-binding-marker-repair` |
| `feature/h616-physical-preflight` | abandoned | `fafb87a02fbc9a25c3e910842af3628e9b00e0fe` | `archive/20261002/abandoned/feature/h616-physical-preflight` |
| `feature/h616-physical-preflight-repair` | abandoned | `035b36ffbc29f511e413efda6d2f6d370a5193a4` | `archive/20261002/abandoned/feature/h616-physical-preflight-repair` |
| `feature/host-admin-bundle-upload` | merged | `01b83b9fe8f45e487e200aa7e01df2025d6d5cd8` | `archive/20261002/merged/feature/host-admin-bundle-upload` |
| `feature/host-admin-cockpit-integration` | merged | `153615d08d41c491a19a87ad227c85891ad463e1` | `archive/20261002/merged/feature/host-admin-cockpit-integration` |
| `feature/host-admin-image-jobs` | merged | `7afb16911aadcbbbb98a2986df3c79c08f7fd925` | `archive/20261002/merged/feature/host-admin-image-jobs` |
| `feature/host-admin-image-jobs-drafts` | merged | `ee5f3827018a6601a978d9067bea4278c7bcfc16` | `archive/20261002/merged/feature/host-admin-image-jobs-drafts` |
| `feature/host-admin-image-jobs-v2` | superseded | `c33be415c07e45d0c17a1a6c40626de33870c924` | `archive/20261002/superseded/feature/host-admin-image-jobs-v2` |
| `feature/host-boot-health-composition` | merged | `316be5fd3824f549a6eb08d5f774e0b6d9a068b9` | `archive/20261002/merged/feature/host-boot-health-composition` |
| `feature/host-recovery-export-composition` | merged | `0c91fff42438964dd6c97de8be55608efed64d63` | `archive/20261002/merged/feature/host-recovery-export-composition-local` |
| `feature/host-recovery-export-composition` | superseded | `4ceec0e0b7b0299d9cfc615e61036ddbb35aa2cd` | `archive/20261002/superseded/feature/host-recovery-export-composition-github` |
| `feature/host-recovery-independent-image` | merged | `922ec9c6a291fe40a6b5c6ba21ad26825b581fbe` | `archive/20261002/merged/feature/host-recovery-independent-image` |
| `feature/host-sd-network-root-implement` | merged | `872b8557fc469b0262a38a8253dd6764c280f1b4` | `archive/20261002/merged/feature/host-sd-network-root-implement` |
| `feature/host-unattended-ab-updates-impl-final` | superseded | `23d8e78285103a67112d80f418f286cce0aee4b9` | `archive/20261002/superseded/feature/host-unattended-ab-updates-impl-final-github` |
| `feature/host-unattended-ab-updates-impl-final` | merged | `47307c438076466bb9daa2ddfdd41bf846b5816b` | `archive/20261002/merged/feature/host-unattended-ab-updates-impl-final-local` |
| `feature/host-unattended-ab-updates-impl-reviewed` | superseded | `1889916553810ff13e46576911b65ab914bad1e7` | `archive/20261002/superseded/feature/host-unattended-ab-updates-impl-reviewed-github` |
| `feature/host-unattended-ab-updates-impl-reviewed` | superseded | `4a6001592c08a760ff41b0f11920b2562d8b4e51` | `archive/20261002/superseded/feature/host-unattended-ab-updates-impl-reviewed-local` |
| `feature/host-unattended-ab-updates-implement-offline` | superseded | `02b4cf1773934a72c6671d9d52cadbb128e40f03` | `archive/20261002/superseded/feature/host-unattended-ab-updates-implement-offline-local` |
| `feature/host-unattended-ab-updates-implement-offline` | superseded | `360a8c0952bf5982d0a42875ce9a1a002b19c3e4` | `archive/20261002/superseded/feature/host-unattended-ab-updates-implement-offline-github` |
| `feature/host-unattended-ab-updates-qemu` | superseded | `6c602ecfaaa703e54d3d737d795aea0e63eedc34` | `archive/20261002/superseded/feature/host-unattended-ab-updates-qemu-local` |
| `feature/host-unattended-ab-updates-qemu` | superseded | `d9c3e7fc70a919a18fbe696b2e1b1c8efc5a4b5b` | `archive/20261002/superseded/feature/host-unattended-ab-updates-qemu-github` |
| `feature/host-unattended-ab-updates-qemu-reviewed` | merged | `2c846cb6c2d805cfb116def84d0d792a7e7f104f` | `archive/20261002/merged/feature/host-unattended-ab-updates-qemu-reviewed` |
| `feature/network-emmc-authenticated-claim-implement-authenticated-receipt` | abandoned | `87dbf37f7db2681b4c93e871c63020590af31a60` | `archive/20261002/abandoned/feature/network-emmc-authenticated-claim-implement-authenticated-receipt` |
| `feature/network-emmc-authenticated-claim-implement-authenticated-receipt-v2` | abandoned | `e00e92a284a05acd80cc89343bd0ff8f79bd6dde` | `archive/20261002/abandoned/feature/network-emmc-authenticated-claim-implement-authenticated-receipt-v2` |
| `feature/network-emmc-cid-admission` | merged | `b0b3ed72b6a1e39f76f43cad955ebbf0b968d28e` | `archive/20261002/merged/feature/network-emmc-cid-admission` |
| `feature/network-emmc-cid-admission-cid-admission` | merged | `71320a888fe95c57c3291bf9b3bb6c674d0962e3` | `archive/20261002/merged/feature/network-emmc-cid-admission-cid-admission` |
| `feature/network-emmc-cid-fd-binding-qemu-cid-fd-binding` | merged | `dcc2c34a98ef3209b1dd3bafde7153565a2b934b` | `archive/20261002/merged/feature/network-emmc-cid-fd-binding-qemu-cid-fd-binding` |
| `feature/network-emmc-fd-binding` | merged | `cdfd03d93ea64e7abeb4720c3793fafc3e2ba547` | `archive/20261002/merged/feature/network-emmc-fd-binding` |
| `feature/network-emmc-fd-binding-evidence-resubmit` | merged | `eb68f7907a955ea848b2ffba673db03130f78707` | `archive/20261002/merged/feature/network-emmc-fd-binding-evidence-resubmit` |
| `feature/network-emmc-fd-binding-qemu-fd-binding` | superseded | `32bbc09734ecec4bb91254d309e07847b3dc2c88` | `archive/20261002/superseded/feature/network-emmc-fd-binding-qemu-fd-binding` |
| `feature/network-emmc-h616-writerless-adapter-commissioning-adapter` | superseded | `0cea0072d7534b24657bc2b10f47c0f747f68edb` | `archive/20261002/superseded/feature/network-emmc-h616-writerless-adapter-commissioning-adapter-github` |
| `feature/network-emmc-h616-writerless-adapter-commissioning-adapter` | superseded | `bc7bb03f29c97a9e2da310d3598bf5f7b44d1074` | `archive/20261002/superseded/feature/network-emmc-h616-writerless-adapter-commissioning-adapter-local` |
| `feature/network-emmc-h616-writerless-adapter-final-review` | merged | `dd2f2be2d5cd3be1e509765453f9bee24438a87e` | `archive/20261002/merged/feature/network-emmc-h616-writerless-adapter-final-review` |
| `feature/network-emmc-h616-writerless-adapter-review-resubmit` | superseded | `850d2eb9c313c7abce6c913dbc5fd8bde0ff5eb8` | `archive/20261002/superseded/feature/network-emmc-h616-writerless-adapter-review-resubmit` |
| `feature/network-emmc-one-shot` | abandoned | `bdb2f42749e691e749433f7e2f9b0e093d664dcb` | `archive/20261002/abandoned/feature/network-emmc-one-shot` |
| `feature/network-emmc-one-shot-resubmit` | abandoned | `bdb2f42749e691e749433f7e2f9b0e093d664dcb` | `archive/20261002/abandoned/feature/network-emmc-one-shot-resubmit` |
| `feature/network-emmc-reimage-mode-qemu-reimage-mode` | merged | `d85b5e572464d1526c2d96266c602b1661dc7fd5` | `archive/20261002/merged/feature/network-emmc-reimage-mode-qemu-reimage-mode` |
| `feature/network-emmc-reimage-qemu` | merged | `b49173f0e662ec83ef5470f3d99f5e565087da46` | `archive/20261002/merged/feature/network-emmc-reimage-qemu` |
| `feature/network-emmc-target-admission-locator-refactor` | merged | `7aa0a605af8fdae2403c93d5d20b8d470760e476` | `archive/20261002/merged/feature/network-emmc-target-admission-locator-refactor` |
| `feature/printer-interface-config` | merged | `72000d3f377f4e773036718b4d6d4d84d3cdc537` | `archive/20261002/merged/feature/printer-interface-config` |
| `feature/recovery-export-readback` | merged | `2a50af2289650b04263d47b6859665d0416c56e0` | `archive/20261002/merged/feature/recovery-export-readback` |
| `feature/recovery-intake-receipt-binding` | merged | `ebaacddf94e5e063e06efb9a03ef3eefbc3c4465` | `archive/20261002/merged/feature/recovery-intake-receipt-binding` |
| `feature/recovery-media-export` | merged | `e54d46c15c68d737b5d844352910ff9ddc33264c` | `archive/20261002/merged/feature/recovery-media-export` |
| `feature/recovery-media-export-fix` | merged | `03cb99996e7ad92eed97c312932463821818ec8e` | `archive/20261002/merged/feature/recovery-media-export-fix` |
| `feature/sd-recovery-reboot-guard` | merged | `b74db5a25ad105d3b78d1066ebd5d4660a346aae` | `archive/20261002/merged/feature/sd-recovery-reboot-guard` |
| `feature/sd-stopped-prompt-resume` | merged | `60ce40420432710aaaadf98862ddb116b87be184` | `archive/20261002/merged/feature/sd-stopped-prompt-resume` |
| `feature/trusted-writer-end-to-end` | merged | `32ef711671981c4ccefecd951f02acb771794b4a` | `archive/20261002/merged/feature/trusted-writer-end-to-end-local` |
| `feature/trusted-writer-end-to-end` | superseded | `6a3e0ed9f284b37879236d3fda93a42e84d17e55` | `archive/20261002/superseded/feature/trusted-writer-end-to-end-github` |
| `feature/trusted-writer-end-to-end-v2` | merged | `8ece67434b92540b219bbf39207049ae35b04eca` | `archive/20261002/merged/feature/trusted-writer-end-to-end-v2-local` |
| `feature/trusted-writer-end-to-end-v2` | superseded | `dac6d6b8bf9f1a96814c99577743224e9f5e0b1f` | `archive/20261002/superseded/feature/trusted-writer-end-to-end-v2-github` |
| `feature/urh-remediation-v2` | deferred | `6d46d33882d7d6d17bbc7ed11a102e8986b0a65a` | `archive/20261002/deferred/feature/urh-remediation-v2-local` |
| `feature/urh-remediation-v2` | deferred | `f4498eeddef35f560ea0f0cb5a6f8538ce1c6c8d` | `archive/20261002/deferred/feature/urh-remediation-v2-github` |
| `feature/urh-stage-and-qemu` | deferred | `d47c0fb4a7c03fc161beb7320b8fe75ecb9abe5a` | `archive/20261002/deferred/feature/urh-stage-and-qemu-github` |
| `feature/urh-stage-and-qemu` | deferred | `e69c0ecb41d303b11e0c72e4566a6b9b9346863c` | `archive/20261002/deferred/feature/urh-stage-and-qemu-local` |
| `h616-evidence-hash-fix` | superseded | `f790af00ff8eb0b92cb3b72f64916fb945015a0d` | `archive/20261002/superseded/h616-evidence-hash-fix` |
| `reconcile/host-recovery-export-record` | merged | `daed4a187cc6c1c70d89ee9e6ab1177617bbd133` | `archive/20261002/merged/reconcile/host-recovery-export-record` |
