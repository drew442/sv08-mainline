# Writerless eMMC reimage boot-route assessment

Date: 2026-09-27. Profile: `test-sv08-01`. Research only; no host or printer
state was changed. This assessment informs the pending
[trusted-writer proposal](../features/network-emmc-trusted-writer-boot/proposal.md).

## Objective fit

The approved objective is to reimage the installed eMMC without removing it or
using the USB writer, with no human action for each write. The existing SD/NFS
diagnostic proves that this board can boot a kernel and initramfs from removable
SD, obtain wired DHCP and mount a read-only NFS root. The H10 probe then exposed
the installed eMMC as `/dev/mmcblk0`. It did not write. A writer launched by the
normal SD boot therefore has a measured route to the target, but requires a
prepared SD card to remain installed and the board to reboot through U-Boot.
This can avoid an eMMC move and USB writer, though it is less direct for a
hands-off service invoked from the running OS.

A kexec handoff from the running host is a closer fit for the no-interaction
goal: a privileged, explicit controller can load a separately authenticated
kernel/initramfs/DTB into RAM, stop ordinary host services, and hand off directly
to a minimal writer system. That initramfs can fetch only the exact read-only
image source from Beelink, verify the complete image and one-shot claim, then
write and read back the still-installed eMMC. The flow would not depend on SD
boot selection or an eMMC boot-policy edit. A failure before the target opens
can halt or reboot to the prior installation; interruption after opening the
target can still destroy its bootable contents and requires the documented
recovery path. This is not a zero-risk or self-recovering write.

## Local kernel evidence

The v5 physical boot record identifies Debian 13 and
`6.18.51-sv08-candidate1` as the kernel actually booted on the printer. The
recorded generated configuration hash is
`e0f0a8bfdc98effeccbe328d165301116de540fe06d68b3e6780593383e46da2`; inspection
of the retained configuration shows `# CONFIG_KEXEC is not set`. Thus the
currently recorded v5 kernel cannot perform a normal kexec handoff.

The retained Debian arm64 `6.12.107+deb13-arm64` kernel candidate has config
SHA-256
`21b2f85fedc3801307af4a27a6ea15bbfdc16cd92d7a0211a5ead1f01dcc3cee`; its
configuration selects `CONFIG_KEXEC=y`. This is package/configuration evidence,
not evidence that the 6.12 kernel boots the SV08 H616 board or supports all
required board devices. The separate 6.18.51 source configuration records
`ARCH_SUPPORTS_KEXEC=y`, so enabling the standard arm64 kexec loader appears
build-feasible for that source. No such image has been built or tested.

Linux's arm64 boot documentation permits an uncompressed `Image` with an
initramfs and device tree. The kernel kdump documentation lists arm64 kexec
support and gives `kexec` examples using an arm64 `Image`. Those sources support
technical feasibility in general, not safe device shutdown, DRAM reservations,
H616 peripheral handoff, or successful SV08 board behavior. The references were
accessed 2026-09-27: [AArch64 boot protocol](https://docs.kernel.org/arch/arm64/booting.html),
[Linux kdump/kexec guide](https://docs.kernel.org/admin-guide/kdump/kdump.html),
and [`kexec_load_disabled` semantics](https://docs.kernel.org/admin-guide/sysctl/kernel.html#kexec-load-disabled).

The pinned 6.18.51 arm64 implementation checks that secondary CPUs can be
stopped before accepting a kexec image, then masks local interrupts and jumps
through the relocation path. It does not perform a board-specific cold reset.
Consequently, a generic arm64 QEMU test would not prove H616 clock, MMC,
Ethernet, watchdog or power-controller state is safe across this handoff. If
this route is approved, first make one reviewed physical **read-only** kexec
boot into a RAM initramfs that reports identity and halts. Only after that
passes should a separate high-consequence review and explicit authorization
allow the one-shot physical write. This should be planned as one owner session
where possible, but the read-only pass must not silently flow into a write.

## Design implications for independent approval

If kexec is selected, the feature must be an explicit, locally authenticated
operation in a host image whose reviewed kernel enables kexec. The controller
must verify an exact signed boot bundle before loading it; the network must
provide image bytes only. The RAM initramfs must contain the reviewed target
adapter, target policy, and claim verifier, and must not switch to executable
NFS root content. It must confirm source availability and all non-writing
preconditions before its first target open. It must then consume the durable
one-shot claim before writing and never retry/rearm after an ambiguous result.
The ordinary diagnostic remains unable to write. The host must not set
`kernel.kexec_load_disabled=1` before a deliberate authorized handoff, since the
kernel documents that setting as irreversible until reboot.

The pending feature approver should decide whether to replace the SD-boot
composition with this single primary route, or retain SD boot as a separately
bounded commissioning/recovery route. Implementing both full writer boot paths
would increase surface area and review burden. A QEMU arm64 handoff can validate
the software transition and synthetic-media write path, but cannot validate the
H616 kexec handoff, actual MMC identity, physical power-loss behavior, or final
printer boot. H12 must continue to require fresh live CID/dev_t comparison,
exact artifact/recovery review, a high-consequence review, and explicit
authorization before one supervised physical write.
