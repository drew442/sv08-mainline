# H12 authenticated intake, 2026-09-30

The owner authorized trusting any SSH host key at the reserved printer address
`192.168.1.141`. This resolves the initial enrollment decision in
[the SD recovery host](host-sd-recovery-host.md); the missed console fingerprint
and earlier failed review remain historical evidence. The coordinator enrolled
the currently offered Ed25519 key in an isolated ignored known-hosts file, then
used strict checking and the existing owner credential through Beelink. Beelink's
default credential was refused; the owner key authenticated successfully.
This decision grants no additional media, boot-policy or printer-output authority.

## Fresh measured state

The read-only inventory at 2026-09-30 11:19:32 UTC reports:

- Kernel `6.18.51-sv08-candidate1`; SD root `/dev/mmcblk1p2`, ext4
  `ro,norecovery`, expected SD root PARTUUID. No failed systemd units.
- Device-tree compatible strings `sovol,sv08`, `bigtreetech,cb1` and
  `allwinner,sun50i-h616`. Board revision `H616_JC_6Z_V1.2` remains the owner's
  reported marking; this SSH inspection does not independently measure the PCB.
- The unique MMC card under `4022000.mmc` is now `/dev/mmcblk2`, device
  `179:8`, capacity 31,272,730,624 bytes. Its CID SHA-256 agrees with the
  earlier installed-spare record. Device names changed; do not reuse the old
  `/dev/mmcblk0` spelling as identity.
- Recovery p5 is unmounted, 536,870,912 bytes, PARTUUID
  `b28438ed-f895-4b93-9bad-d27d3890ccd3`. No eMMC partition was mounted.
- The shared GPT parser passed both header CRCs, array agreement, partition
  geometry and SPL/environment collision checks against the reviewed
  7,818,182,656-byte image footprint. The backup GPT remains at that image
  footprint, rather than at the spare's full physical capacity.
- Both 64 KiB redundant environment records pass CRC. The 4 MiB copy has
  flag 3, order A, A=3/B=0; the 8 MiB copy has flag 2, order A, A=2/B=0.
  These bytes agree with the earlier intake. They are **not exhausted** and
  cannot satisfy physical preflight admission until a separately reviewed
  boot-policy operation prepares the required state.
- Linux UTC and the `sun6i-rtc` sysfs clock both report 11:19:32 on September 30.
  This is fresh clock/readback evidence, not proof of cold-power retention.

Raw CID, fixed-offset reads, collection source, stderr and owner authorization
are retained in ignored
`local/feature-workflow/probes/h616-physical-preflight/h12-access-20260930/`.
The sanitized inventory is `inventory-sanitized.json`; the complete shared-parser
result is `gpt-validated.json`. No private key material was read or transferred.
No eMMC, raw environment, boot-policy or MCU write, reboot, heater or motion
operation occurred during intake.

## Reviewed recovery inspection and next operation

The medium `high_consequence_reviewer` first returned FAIL because a
mount-source spelling check could miss alias mounts. The original script and
failed verdict remain preserved. The corrected exact script checks disk/child
major:minor identities across visible PID mountinfo, the actual p5 block identity,
PARTUUID, capacity and parent, plus separate private mount namespace and
propagation. It received PASS WITH CONDITIONS. Coordinator runtime evidence
confirms `high_consequence_reviewer`, GPT-6.1 Sol, medium, full access with
approval never; these are measured runtime settings, not a profile-file claim.

The coordinator then executed the exact reviewed script with assertions enabled
under `unshare --mount --propagation private`. Fresh host PID/proc visibility and
exclusive coordinator operation were checked. p5 mounted only in that private
namespace as ext4 `ro,nosuid,nodev,noexec,norecovery`; original `recovery.scr` is
720 bytes, SHA-256
`57e414bec126a309085f3e2be211c6b8fe0e43f5833a5b5609f3e69457808dee`.
It has 154,374,144 bytes available. Unmount and temporary-directory removal
completed before success was reported. The command and SSH both exited zero;
the global mountinfo hash remained byte-identical. There was no filesystem
journal replay, persistent write, boot change or reboot.

Beelink's regular `image.bin` was separately rehashed and matches
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`;
its NFS service is active and export lists read-only/root-squash access for the
printer. Beelink has 1,611,685,888 bytes available at this observation, so avoid
another full-image allocation. The serial device is present, but no receive-only
collector process was observed; capture must be restored before any boot action.
Neither the export listing nor an earlier local NFS pass proves a fresh printer
NFS read.

The inspected source still fixes signed policy, live stage admission and compiled
writer paths to `/dev/mmcblk0`. Current `/dev/mmcblk2` therefore cannot enter that
path. The [bounded node-binding repair](../features/h616-emmc-node-binding/proposal.md)
is submitted for independent scope approval; no policy falsification or node
alias is permitted. Actual preflight job/key creation, artifact staging, counter
exhaustion, arming, FIT entry and recovery return remain separate H12 steps.
