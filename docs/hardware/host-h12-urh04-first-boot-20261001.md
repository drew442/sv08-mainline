# H12 urh-04 first physical attempt

2026-10-01, test-sv08-01. **Failed before preflight FIT entry.** No urh-04,
urh-05, printer commissioning or release acceptance is claimed.

The [standing owner authorization](../decisions/20260930-h12-urh04-standing-authorization.md)
covered the [identified operation plan](host-h12-urh04-operation-plan-20260930.md)
with unchanged PSU-off/USB-host-power/Ethernet/spare-installed/factory-stored
setup and no new irreplaceable data. Board revision H616_JC_6Z_V1.2 remains
owner-reported; no hardware profile is qualified.

## Completed separate operations

The fresh job was `8bd9a5860bc40abf37f14e5011544d18`, expiry00:47:49UTC.
The [candidate record](host-h12-preflight-candidate-20260930.md) binds its actual
build/FIT/source hashes. Each operation had a separate exact independent review
with current GPT-6.1 Sol/high runtime confirmed and a recorded one-shot intent.
New-agent thread limits required continuing existing independent reviewers;
they remained separate from author/operator/evidence producer. Historical low
then high contexts of the p5 reviewer remain preserved; current settings were
checked before relying on each verdict.

- Volatile transfer and separate27-file hash/ownership/object-set postcheck passed.
- Private p5 staging passed. Independent readback verified original720B script,
  new48,902,416B FIT,1250B wrapper, clean unmount, absent marker and unchanged raw
  redundant environments.
- Accepted environment arming passed. Independent readback verified both CRCs,
  flags5/4, exhausted counters, exact job token and only the four authorized field
  changes. Raw before/after records were in the volatile target journal; their
  hashes and independent readbacks are retained privately, while the volatile
  journal was lost at reboot.
- Marker activation and independent readback passed: exact18B marker,
  marker-durable journal, unchanged environments/files and clean unmount.
- Actual expiring claim service/PID/start/socket, exact persisted state/source
  hashes, freshly rehashed source image, read-only NFS export and unused claim
  passed. No readiness POST was sent. Response authentication does not provide
  requesting-client authentication; premature LAN consumption would stop the run.
- The bounded UART collector had the sole read-only descriptor, correct CH340
  topology/source/unit and no errors before boot. One ordered SSH
  `systemctl --no-block reboot` returned zero; no force option, HID or UART TX ran.

The first refreshed stage packet had stale FIT constants and was rejected before
execution. Its corrected separate packet passed. Later exact source admission
caught bytecode caches created by the coordinator's inspection helper without
`-B`. The helper was corrected; independently reviewed removal of only the nine
inventoried volatile files/three directories restored exact source inventory.
The original packets, failed receipts and cache inventory remain evidence.

## Measured boot result

UART recorded one SPL/main-U-Boot and original recovery kernel boot. U-Boot
reported1GiB DRAM and two bad-CRC/default environment loads from **MMC(0)**.
It read and executed the1250B staged wrapper, then immediately read and executed
the preserved720B recovery script. The original kernel mounted `mmcblk2p5`
read-only without journal replay. No preflight FIT entry, marker-consumption
result, C preflight result or `PREFLIGHT_PASS` appeared. Separate server inspection
confirmed the exact claim descriptor remains armed and unused.

This demonstrates original-script fallback, not preflight automatic return or
physical read-only target admission. Recovery GUI visual confirmation is pending;
the passive KVM snapshot endpoint was inactive and its API required authentication.
No credential material was read. Marker/environment retention after this boot is
inferred from pre-entry fallback, not a new direct media readback.

## Source-backed explanation and next repair

Pinned U-Boot `ece349ade2973e220f524ce59e59711cc919263f`,
`board/sunxi/board.c:537`, selects environment device0 when booting SD
(BOOT_DEVICE_MMC1), and device1 for eMMC. The configured index is only its default
case. `env/mmc.c:465` uses that selection for redundant environment loading.
The selector's first guard requires the job token and exhausted counters from
RAM environment before reading the marker/FIT. Thus the valid armed records on
the spare do not become the guard's environment on this SD boot. Individual
in-RAM predicates were not printed; the precise failed predicate is inferred
from source/defaults and observed fallback.

Primary source excerpts/hashes, actual loader configuration and UART are retained
privately. Sources accessed2026-10-01. The required
[selector environment repair proposal](../features/h616-selector-environment-source/proposal.md)
uses existing upstream MMC reads and CRC-checked whitelisted import of both
intended records, preserving every marker/FIT/purpose/fallback check. It is
approved with constraints for offline implementation; fresh independent delivery
verification remains required. No upstream source/loader has changed.

The failed attempt stops without retry, rearm, another boot, marker removal or
whole-image write. Preserve all evidence and let the expiring service stop.
Future recovery/SD return and replacement physical attempt require their own
exact reviews/current admissions under applicable standing authority; the failed
job must not be reused. H12 remains in the existing human queue.

Private evidence: ignored
`local/feature-workflow/probes/h616-physical-preflight/h12-access-20260930/physical-candidate-refresh-f6927b8b/`,
including `urh04-physical-result.json`, action/readback receipts and capped UART
snapshots. No private signing inputs, raw device identity or generated images are
published.

## Subsequent offline repair acceptance

The required repair passed fresh independent `feature_verifier_high` review at
`9995239278b7470d1bf64ee76901dc9ae91d959a`, with actual GPT-6.1 Sol/high
runtime recorded, and was merged locally. [The source-bound delivery](../design/unattended-emmc-reimage-handoff.md)
includes 43 actual U-Boot cases, 62 focused regressions, independent compiled-selector
before/after reproduction and representative artifact/member verification.
This later offline acceptance does not change this failed physical result.

Read-only follow-up confirmed the expiring claim unit inactive/dead, PID 0 and
exit 0; it was not restarted. Printer SSH banner timed out, and the passive KVM
snapshot endpoint remained unavailable. Original recovery GUI observation and
current raw media reconciliation remain pending.

The failed FIT's exact bytes/hash are retained in a private persistent Beelink
archive after independent readback and fsync, with a verified volatile local
cache at its original logical path. Archive and restoration receipts record
that the cache is temporary; no historical candidate was discarded.
