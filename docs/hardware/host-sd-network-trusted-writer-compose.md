# Trusted writer SD composition (offline prototype)

The explicit commissioning path takes an inert H616 writer bundle from
`build_h616_reimage_candidate.py --trusted-initramfs --source-server ADDRESS
--source-export /PATH` and composes it with
`build_sd_network_image.py --commissioning-root BUNDLE --claim-port PORT`.
The two commands require the other existing builder inputs. The exact NFS
server and export must match in both commands. Keep private policy, keys and
jobs under ignored `local/`; this path has no physical authorization.

The ordinary SD diagnostic composition is unchanged and contains no writer.
Commissioning unpacks and repacks the pinned Debian initramfs as one gzip/newc
archive with normalized metadata. U-Boot hashes the complete SD initramfs before
boot. The archive holds the writer,
policy, signed job, signature and expected image digest. It replaces the
initramfs-tools `init-bottom/ORDER` file, which `/init` sources after mounting
the specified NFS export read-only at `/root`. That file `exec`s the embedded
writer from PID 1, with a terminal loop if exec fails, so the normal `run-init`
handoff cannot execute the NFS root. The writer requires an initramfs root, the exact NFS mount
source and read-only mount flags. It rechecks the mount and source descriptor
before its sole target open. The NFS export is an image source containing
`image.bin`; no executable from it is invoked. A writer result is terminal
while the SD card remains installed. There is no automatic return to eMMC boot.
Commissioning boot arguments select `boot=nfs` for the trusted initramfs-tools
mount logic but set the kernel fallback root to `/dev/ram0`. If `/init` is absent
or fails, the kernel cannot fall back to running an NFS-supplied init.

The composed image remains an offline prototype. Hashes stored on the same SD
card detect changed payloads only while that card stays in owner custody; no
SoC secure-boot root authenticates a substituted card. The path has no live
CID/dev_t, physical write, power-loss recovery or release evidence. H12 still
requires fresh identity comparison, exact artifact and recovery review, an
immediate separate high-consequence review and explicit owner authorization.

Offline validation on 2026-09-27: 26 focused composer/H616 tests and 21 existing
SD writer/CID/probe regression tests passed. Repacking the pinned 15,233,015-byte
diagnostic initramfs with a disposable dummy bundle produced a 15,109,645-byte
archive; both `lsinitramfs` and `unmkinitramfs` recovered the trusted PID 1
`ORDER` file and writer. Repeated composition from identical inputs produced an
identical SHA-256. This tests archive construction and parser behavior, not an
H616 boot or a physical write. The extracted initramfs occupied about 54 MiB of
scratch space; the builder also retains an uncompressed newc archive and the SD
image, so the release/commissioning build needs a separate scratch-budget check.
