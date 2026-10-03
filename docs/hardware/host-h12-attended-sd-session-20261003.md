# H12 attended SD session preparation — 2026-10-03

Status: physical preparation. Software delivery verification passed and the
tool is merged on main. Exact physical-action review is pending. No full-image write or restart is authorized by this record.
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
