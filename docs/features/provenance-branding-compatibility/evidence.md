# Stock Cockpit branding compatibility — 2026-10-27

Owner requested deployment of merged PR35 (including PR34). Preflight reached sv08@192.168.1.141 on healthy non-trial slot B, immutable root `/dev/mmcblk2p4`,724MiB root/1.8GiB data free. Cockpit socket active; printer/Moonraker/nginx/observer inactive with original masks.15protected configuration/state paths were hashed. No printer software, root mount, service configuration, identity or stored user data was changed during this attempt.

## Demonstrated defect and correction

Merged validator refuses `usr/share/cockpit/branding/debian/favicon.ico`, a stock link to `../../../pixmaps/debian-logo.png`. logo.png has the same vendor link. Neither is part of the installed project's existing recorded inventory; only project badge.svg and branding.css are recorded there. Walking all vendor branding files makes ordinary factory assets a false project-integrity failure. The earlier disposable fixture normalized these vendor links within its own image, so it did not expose this installed compatibility issue; those historical results remain unchanged.

The correction scopes the external shared branding directory to its two explicit project-owned filenames. It preserves strict symlink/path/hash checks for project assets and the existing full project-prefix inventory. It does not rewrite/normalize vendor assets or ignore arbitrary files inside project runtime/UI directories. A regression asserts the fixed allowlist matches actual project branding source assets, so adding another project branding file requires updating the coverage.

## Actual checks

- `python3 -B -m unittest discover -s tests -p 'test_project_license.py' -v`:23PASS,0.498s. Stock vendor symlinks allow preparation/validation/intact; vendor-only changes remain outside project scope; project branding edits/symlinks still taint. Existing record, source/license and unknown-bytecode protections pass.
- `test_stage_admin_ui.py`:22PASS,2.202s. `test_stage_printer_ui.py`:13PASS,51.538s. Total58checks; diff inspected and `git diff --check` passes. UI was not changed; PR35's source-bound browser evidence remains applicable to presentation, not relabeled as live browser proof.
- Coordinator evaluated the candidate validator read-only against the actual installed root via isolated `python3 -I -B` stdin; candidate was not installed. After the vendor-scope correction,126actual runtime/project inventory entries can be inspected. Every108recorded entry matches, none missing.18additional `usr/lib/sv08/__pycache__/*.cpython-313.pyc` files are correctly identified as unrecorded drift: status remains Tainted. No bytecode exclusion or clean-status override was introduced. This check does not prove who/when generated those pre-existing caches.

No authenticated owner-browser session or physical outputs were exercised. No deployment or independent operation assessment is claimed: the consequential write gate was never reached. The root remained read-only and existing services/masks/configuration stayed in place. No images/tools/installers, private-key/account inspection, firmware or heater/motion operations.

## Deployment handoff

Deployment remains authorized by the owner's request but is incomplete. Publish this fix for owner integration; do not automatically merge or install an unmerged correction. After merge: recheck current target/state and preimages; prepare exact merged UI/runtime/notices/provenance payload, backup and remove only the18matched unrecorded generated cache preimages as part of the reviewed runtime replacement (recheck actual list; never blanket-delete owner files); preserve stock vendor links and protected data. Obtain independent assessment of the exact write/rollback plan before changing root. Then apply, restore read-only, verify exact hashes, ordinary finite provenance read Intact, protected configuration/CA/services and HTTPS. Do not fabricate source/release qualification from a local intact status. Existing deployment rollback archive from PR33 remains untouched.

Primary allowance1200process-seconds/256MiB across this attempted deployment and correction; scratch `/home/drew/.sv08-pr35-deploy`,84KiB before evidence. No native goal was created/replaced. One coordinator implementation, no new worker or mandatory source review. Source fix self-validated; deployment still needs its separate operation gate.

## Evidence SHA-256

Private nonsecret artifacts are retained under the scratch path; full protected-path metadata is not copied into the public PR. The first failed symlink exception is in the coordinator tool output and preflight.py reproducer; corrected read-only results and diagnostic list are retained separately.

| File | SHA-256 |
| --- | --- |
| `preflight.py` | `598616dc173660c984b445dbdd0b8fccf735e845b23caffb20241f6c9090055e` |
| `preflight-fixed.py` | `3a2fc15f0445546bb9b4eec17b709dc983e696cfdb8b60da3ddb1af0c828d035` |
| `preflight-fixed.json` | `5c37141d81d14a4fc3592791244845ad0f00913d27ed9cde2fb4f042ef10bdc6` |
| `diagnose.py` | `36ccd12380fbb06a6635be44405b9838c36ab502d6743a52a661a9a83a389f99` |
| `diagnose.log` | `b551f673b4b993dc2be74cf0ff188c37ca0fd906a95a3a833c8038f32b9b78f4` |
| `compatibility-tests.log` | `a26fc8d1ecd90615547b8e5a693707aeb5c1cff9c7f6f04d504cec39f6e2a113` |
| `stage-admin.log` | `a0b97cbc544c1d6ed86dbc28168ec5f8e86e918319e02378eb91a946e690285e` |
| `stage-printer.log` | `c7457655ea6a5b10543def58b76a932c3ac07a4070479ce68de00bdc2836b214` |
