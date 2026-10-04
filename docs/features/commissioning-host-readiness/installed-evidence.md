# Installed commissioning-host acceptance — 2026-10-04

Execution passed; independent final delivery review pending. Named hardware is
**test-sv08-01**, host board **H616_JC_6Z_V1.2 owner-reported**. This establishes a
bounded diagnostic host ready for subsequent sensor commissioning, not a supported
release or printing system. Exact private receipts are hashed in
[installed evidence JSON](installed-evidence.json); machine serials, credentials,
raw banks, inactive sensor config and screenshots remain ignored/private.

## Boots

Initial installation retained exact beforeimages and restored root read-only.
The first helper refused before writing because an older valid bank contained
historical non-counter values. The independently reviewed history repair preserved
the selected environment and original failure evidence, then confirmed A3 once.
The first normal restart booted Linux/SSH but exposed volatile mmc numbering;
the helper refused before writing. That failure remains recorded. The independent
[stable-device repair](stable-device-repair.md) binds controller/CID and verifies
the current disk identity at every probe. Its exact three-file installed readback,
selected-tool/dependency identity and explicit failure reconciliation passed.

After repair, a second normal restart and one five-second HW-667 power cycle
passed automatic confirmation. Their distinct boot IDs are respectively
b855f055-da62-49f4-af97-bdd2afd69e1a and 2e1e3701-e7a3-4999-8fa5-107360d3a8b5.
The normal boot selected A3/B0 with older bank A2 and flags7/6; the relay boot
selected A3/B0 with older A2 and flags9/8. Both CRCs passed, selected non-counter
logical values were unchanged, A-only state/generation was preserved, and root
and paired boot were read-only with data writable. The relay enumerated the same
eMMC as mmcblk2, exercising the stable identity repair after mmcblk0/mmcblk1.
Seven masks stayed active and corresponding printer/update services inactive;
no production readiness marker, trial, backend activation or active printer.cfg.
Full boot-B, root-B and recovery hashes match the pre-install baseline. GPT and
partition/controller/CID checks passed. These are two healthy bounded transitions,
not full A/B failover, power-loss or long-term reliability qualification.

## Access and theme

Actual authenticated SSH and Chromium Cockpit login, administrator elevation,
connected host status, Stop administrator access, logout and relogin passed
before and after the accepted normal/relay transitions. Login and host branding
were checked at 1024×600 and 1440×900. Persistent marker, SSH public identity and
TLS public fingerprint matched across boots. The owner-requested simple password
was set privately on this installed account and persisted; it is not in the image
or repository. This follows the [owner amendment](owner-access-amendment.md).

The narrow immutable-root TLS directory repair and fixed admin context were
verified against exact installed files. Cockpit required one reset of its earlier
socket failure after repair. Existing page limitation: a stale authorization notice
remains after successful elevation, while actual authority/status are correct.
Image staging is explicitly unavailable until its verified OS backend is integrated.
No browser host operation was applied. These limits do not claim full update UI
integration or alter its accepted requirements.

## Matching software and inactive sensor configuration

Host package sv08-klipper 0.0+gitf0892d82-1 verifies and records full source
f0892d82b0f1c1228454f09eb508eddde2250f4b. The installed prebuilt C helper matches
its retained SHA256, and timestamp selection does not request a rebuild.
The packaged venv belongs to the same verified package.

On October 4 the owner authorized autonomous mains control through Beelink
/usr/local/bin/sv08-power and confirmed USB/Ethernet/media unchanged. Separate
Sol6.1/medium [power amendment review](reviews/20261004-power-review.md) passed;
effective full role/model/effort were verified. The utility SHA256 is
512ae106d30cf572f65eb400fd8955a27c2937bf9179f3090cfd2fd933f2acea.
Owner mapping identifies the plug with the PSU; status is not an electrical
voltage measurement. USB relay was left on and no relay command was sent.

At 04:08:51 UTC the ON command succeeded and separate status returned ON.
Two exact previously recorded MCU by-id identities appeared as distinct ttyACM
character devices. Fresh package/helper/root/masks/idle checks passed. The reviewed
script ran once per device under a 15-second timeout, mainboard first, validating
its result before toolhead. Both report f0892d8, 139 commands, matching retained
compiler metadata and identical uncompressed dictionary SHA256
86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b.
Only identify requests were made; no MCU config/reset/flash/output command.
Transport may retransmit identify requests. Dictionary matching reconciles protocol
and build metadata, not the entire flash image, bootloader or measured oscillator.

OFF succeeded at 04:09:05 UTC and fresh status returned OFF. The host retained
its relay-test boot ID, root/boot read-only, masks/inactive services, no active
configuration and closed serial ports. Only mainboard remained enumerated after
PSU off, consistent with retained USB power. No failed query or corrective power
attempt occurred. PSU off is not whole-printer isolation: USB still powers H616.

The private modified-printer input-only configuration already passed installed
ARM64 file-output parsing using both matching retained dictionaries (exit0;
87/86-byte outputs). It contains temperature/input sections, no heater/stepper
outputs, and remains inactive. This is parsing evidence, not live sensor accuracy,
verified wiring/polarity/thermistor circuits, input transitions or safe heating.
Those physical H05 checks follow separately. No general printer service activation.

## Preserved requirements

H12 stays complete. SD recovery remains sufficient; no RAM maintenance,
anti-forgery/replay/RNG, cold-capture or deferred automatic launch/return was
reintroduced. Original failed observations and rejected reviews are retained.
Matching host/MCU builds remains the policy for image A/B; different Klipper
revisions require matching MCU artifacts or a separately tested compatibility
policy. Switching host slots alone does not switch MCU firmware.
