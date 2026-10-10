# Assembled update and reboot reliability evidence

Delivery details and reproduction boundaries are in [host
reliability](../../hardware/host-reliability.md). Installed runtime and the native
closure are bound to `f67cdf77178e83f26e3cc48b1f8bf338d32e8feb` (manifest
`f0181f186bb9b43c22c46925eb69dd18c8c46e5ea921c0814ca306cb66d1695c`). Final fixture-only
continuation source is `655f2a6f33a151f1996c4d7c83d0c2247d184c10` (89-file manifest
`5cb67f4e2c77d1b034f9d5062265453129ae32ec02e1270501976ede2fdffe48`). Intermediate
fixture correction/resume source was `9ba8a7bda29537147f6b2612a1db4bd48aec9ff9`
(manifest `a9c27b05b8a1ad02d6f0ac3ebbedce92b93cd2802502396a2a0929f79c172643`). All 65
installed runtime/image inputs and the bundle root-construction function are unchanged
between these revisions. Later documentation-only publication does not change these
executed bytes.

## Acceptance mapping

| Check | Evidence | Boundary |
| --- | --- | --- |
| coordination | 258 native checks passed in 20.310s; controlled restart/lost acknowledgment, state/ledger admission, package/mode/network exclusions, normal healthy-boot refill and private SQLite/WAL snapshot checks | Native services are simulated |
| assembled-arm | 12 accepted actual ARM boots (14 attempts; two fixture failures retained), exact receipt `3810dd24…` and original preservation hashes | Actual Linux/systemd/ARM RAUC and redundant environment; printer status and slot-selection driver are simulated |
| storage-publication | Final ledger and exact goal-owned retirement passed; source/docs publication bound by canonical workflow evidence | Goal-owned scratch only; no historical images or shared base deletion |

Native log SHA-256: `5c8be8ab0f59d7b9d41618572c49c00a629722a5102d76f10b4899e0ed1dca55`.
Full command is recorded in the linked hardware evidence. Source/test changes were
checked with `git diff --check`; no gitlinks or pinned upstream sources changed.

## Exact disposable-system inputs

| Input | SHA-256 / revision |
| --- | --- |
| Shared read-only ARM base | `86ba63ee4dd06eb8116f540acc3129d9ba4b39a8d070c98d19afe691251452a5` |
| Kernel | `9c37ace54ef7e1919411fd912e9f34d6982ddd7f4c8ef3c8aee56f4c4d70db67` |
| Initrd | `470d669587382bdf662fceaff09efd0fee8cd5aa58ac69a87bf1ea7744903142` |
| Native RAUC builder 1.15.2 | `c4cca3b8e5674504d954fb0b0d5b8552eca800a8fd576be97f11585bd33e5c96` |
| ARM RAUC 1.15.2 binary | `51d7c057c7fb00917287b5324303c747e71c5406f4c1363a678578ac7a3b12e3` |
| Klipper | `f0892d82b0f1c1228454f09eb508eddde2250f4b` |
| Healthy signed bundle | `e9d78f54011e38ffb118d42ed9747fa5b02920a7cb3393f32e4fe5747c0a1105` |
| Unhealthy signed bundle | `cc65332a9f8e0017bbb24b193a0d25fd6e1295d16d2d9baa61dfa3098e5636ac` |

The explicitly nondeployable test profile uses synthetic device identities and fixture
signing keys. No private printer credentials, backups or dumps are inputs.

## Retained failed attempts and corrections

Missing public squashfs dependencies and a disposable ext4 block-size invocation were
corrected during construction. Initial native scratch-permission errors were corrected
without relaxing production checks. One new regression test had a mock signature error;
it was repaired and the final changed closure passed in full.

A first journey used an invalid identity argument and failed before staging. A second
hit its original install deadline; the real installer journal remained `installing`. The
next superseded source run was stopped before state mutation. A one-time, explicitly
recorded source-counter reset prepared the old exhausted fixture for the subsequent
test; it was not production confirmation or evidence of ordinary-boot success.

The later `a2fb618` journey actually cancelled that interrupted install on a new boot,
preserved source state, completed signed staging/arming/restart exclusions, and
confirmed the update with late configuration and committed SQLite WAL data. Its third
boot failed preparation without publishing a generation. Native reproduction against its
exact archived source showed that opening a closed WAL-mode source database read-only
created an empty WAL and triggered the strict source-fingerprint refusal. The generic
ARM console did not retain that detailed Python error; the native mechanism is
consistent with the retained ARM state, not a claim that the missing ARM stderr was
observed. The final source recovers only private copied databases, preserves the
source-change guard and reserves its workspace. The failed fixture was retired before
the fresh final sequence.

## Independent assessment and limits

The workflow records the canonical targeted-review outcome in
[record.json](record.json), bound to the submitted evidence digest and accepted
authorization basis. The reviewer did not author the implementation; source review found
and checked repairs to lost acknowledgment, ordinary-boot counter exhaustion and SQLite
workspace accounting. Review feedback was not treated as independent final acceptance
before the executed receipts and canonical evidence list were available.

No live printer operation or deployment occurred. Actual board SPL/U-Boot execution,
electrical power cuts, physical fallback/recovery, printing and MCU communication remain
unqualified by this work.

QEMU-only timing overrides are explicit in the linked evidence: coordinator 180s versus
production 50s, host-health 120s versus 40s, and health-unit timeout 240s versus 60s;
the stability window remains 5s. No production timing/performance qualification is
claimed.

The fresh run accepted boots 1–6, then rejected boot 7 on a fixture Admission
context-manager invocation error before package/interruption/customization checks or
phase publication. The corrected fixture resumes the exact disk using hashed
receipts/logs, original GPT/recovery baseline, immutable runtime-input mapping and full
disk/environment identity checks. It preserves the failed boot separately: final
acceptance is six initial accepted boots, five accepted boots in the first continuation,
and one final continuation boot, with fourteen actual boots in this fixture lineage. The
new continuation manifest raises the host health-boot deadline from 180s to 300s for
deliberate failed normal health plus same-boot healthy retry; old deadlines/results are
retained. No signed image rebuild, source-counter reset or repetition of the six
accepted boots is involved.

The first continuation accepted 7–11 but rejected 12 on the low-space fixture assertion.
Its default tmpfs permissions caused ancestry refusal before the capacity check; the
original error was swallowed by the fixture assertion. Native reproduction confirmed
default permissions/ancestry refusal versus private 0700/real capacity refusal, both
preserving state. Guest-only correction `655f2a6f33a151f1996c4d7c83d0c2247d184c10`
(89-file manifest `5cb67f4e2c77d1b034f9d5062265453129ae32ec02e1270501976ede2fdffe48`)
logs the exact capacity/error/mode. A second full-disk/environment checkpoint retains
all eleven accepted boots and both discarded attempts. Its SHA is
`736b1e61a7d9e6c0fb7e9c62ca6f671f17db34f633a39dc555d867df8d65e425`; the first checkpoint
is `5d43af62de6bb2f3fff487b2a1bfbdf0209bfebbcc9ec33ed86080ec9c81c2a3`.

Final ARM result SHA-256:
`3810dd24a84c197988af1efaac9a364091a7e39b9ed1d83ea4d5dbf18fe049ca`. The linked hardware
evidence maps all 12 accepted boot outcomes/timings and preservation limits; the last
log is `8ed54e5e22fb5acfe38da43a38f4fc338347949e82c9c6c9cf24735de06a4aa1`.

Final cleanup SHA-256:
`f5c1003256dac950de52885d8faf7ca3bf1b8faea33f73edc11404da2d86383f`. Reclaimed
6,025,523,200 allocated bytes; retained 14,344,192 bytes of small artifacts; codex free
34,067,333,120 bytes. Cumulative 29,846,790,144 bytes and charged integration 4119.593s
retain all prior history/conservative bounds. No VM/mount/loop remains. Initial
codex/beelink free-space checks and every image-stage codex reserve check informed
placement; no historic/shared image deletion occurred.
