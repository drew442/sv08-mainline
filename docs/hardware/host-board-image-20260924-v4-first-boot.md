# v4 host-image first physical boot

2026-09-25. Test printer 01, owner-reported host-board marking
`H616_JC_6Z_V1.2`. This documents one physical boot attempt; it does not promote
the diagnostic image to a working host or release. The image/write record is
[host-board-image-20260924-v4.json](host-board-image-20260924-v4.json).

## Observed boot result

The spare eMMC had been written and fully read back on Beelink, then reinstalled
in the printer. A root-owned receive-only 115200-baud serial capture was running
before the powered host was observed. The factory eMMC remained stored.

On the first captured attempt, SPL reported 1 GiB DRAM as one rank, 32-bit,
10 columns and 15 rows. U-Boot 2026.07 selected slot A with one of three tries
remaining. Linux `6.18.51-sv08-candidate1` started with the expected A root
PARTUUID. The expected data PARTUUID mounted read-write at `/data`, then
`sv08-prepare.service` failed. Its required network and login services did not
start, and the unit's configured failure action caused a reboot.

On the next attempt, SPL reported 1 GiB as two ranks, 32-bit, 8 columns and
13 rows. U-Boot then reported `No valid slot found` and dispatched the independent
recovery image. The recovery GUI is visible through the GL-RM1V2. Its message
that `/data/sv08/state.json` is unavailable is from recovery's isolated runtime;
the built data filesystem contains that file. Recovery also reports that its
`recovery-media-policy.json` is absent. Neither message establishes corruption
of the eMMC data filesystem.

The serial capture shows the service failure and slot-selection outcome, but
does not include the service's Python exception or a `systemctl status` report.
Offline inspection found a likely direct cause: v4's root filesystem contains
the rendered `scripts/local-bottom/sv08-data` hook and has an empty
`/etc/machine-id`, but the exact boot initramfs copied into the image does not
contain that hook. The hook is responsible for mounting `/data` early and
binding the persistent machine ID before PID 1. `sv08-prepare` later creates or
loads the persistent identity and explicitly fails if `/etc/machine-id` does
not match it. The original v4 finalizer now reproduces a rejection because the
boot initramfs omits this hook. The traceback itself was not captured, so the
runtime exception remains unmeasured.

The offline data image has `/sv08/state.json` (116 bytes), and its filesystem
hash matches the recorded v4 component; device-side contents after boot have
not been read back. The recovery GUI's missing-state message is still not
evidence of eMMC data loss.

## GL-RM1V2 EDID adjustment

At the owner's request, the GL-RM1V2's 2560×1440@60 `2k60` EDID was replaced
through its supported LT6911C EDID updater with a custom 256-byte EDID. It
advertises 1024×600 at approximately 60 Hz (48.96 MHz GTF timing) as the
preferred mode and basic two-channel LPCM audio. The GL updater returned
`write edid success`; the KVM's persisted custom EDID is under
`/etc/kvmd/user/edid.txt` and matches private artifact
`local/test-sv08-01/kvm-20260925/edid-1024x600.bin` (SHA-256
`932c187a061cf4b042667486f723d3a6663bf2636c274338b79e7531cdb669f9`). The
previous 2560×1440 EDID is preserved privately for rollback.

This timing is a generic 1024×600@60 GTF mode. The exact touchscreen model and
its accepted timing have not been identified, so native panel compatibility is
not yet measured. The GL-RM1V2 capture still reports a 2560×1440 camera frame;
that is the KVM's capture format and does not prove the printer's HDMI output
mode. The connected system must reread the EDID, and its actual selected mode
and the touchscreen image remain to be verified on a subsequent host boot.

References checked 2026-09-25:

- GL.iNet, [How to set EDID for KVM](https://docs.gl-inet.com/kvm/en/tutorials/how_to_set_edid_for_glkvm/),
  which documents preset/custom EDID support and limits of 2560×1440@60, at most
  two blocks, progressive timing, and the audio requirement.
- Watterott HDMI Adapter, [`EDID_1024x600` for HY070CTP-HD](https://github.com/watterott/HDMI-Adapter/blob/master/software/EDID-Prog/EDID-Prog.ino#L695-L710),
  used as a panel identity/timing reference only; the printer touchscreen has
  not been identified as this model. The applied 60 Hz GTF timing is documented
  in this record and the private artifact above.

## Next checks

- Read the exact `sv08-prepare.service` exception on a future A boot, or improve
  the image's early-boot failure report so it preserves the failing operation
  before reboot. The build pipeline now regenerates the initramfs after
  integration, and finalization rejects one without the identity hook. The
  corrected root tree passed this offline check; a complete replacement image
  still needs independent review and physical boot. Do not infer that the
  missing recovery state message is the cause of A's failure.
- Re-arm A only through a separately reviewed, identified target operation;
  current A attempts are exhausted. Preserve the factory eMMC.
- On a subsequent boot, record the DRM/HDMI mode and confirm the touchscreen
  image. If the custom EDID is not accepted, restore the preserved `2k60` EDID
  using the GL-RM1V2 EDID updater.
- Identify the touchscreen model or read its EDID before treating the generic
  1024×600 timing as validated for the physical panel.
