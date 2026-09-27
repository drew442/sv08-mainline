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

## Manual one-shot host service

`scripts/prepare_h616_reimage_job.py` prepares one short-lived signed job from
an exact raw image and a canonical target policy. Its default action is an
inspection that creates no state. `--execute` writes new owner-only state below
ignored `local/`, including the signed job and durable armed claim. Physical
preparation must run as root, with root-owned 0600 policy and key files. The
policy's image hash and partition map must match the reviewed v5 image; the
program streams the complete raw image to check its hash. It will not replace
an existing state directory or silently renew a job. Synthetic policies are
accepted only through the Python test interface, never through the physical
command line.

`scripts/serve_h616_reimage_job.py` also defaults to inspection. An explicit
root `--execute` requires the same image, job verification key and receipt
signing key, an unused prepared claim, an empty export destination, the one
printer client IP, and installed `rpcbind` and NFS-Ganesha executables. It
rechecks the full source hash and claim before writing a durable start marker.
That marker records the exact NFS-Ganesha and `rpcbind` executable hashes.
The NFS export contains only a hard link named `image.bin`, defaults to no
access for other clients, and grants the one printer IP read-only access. The
raw image must be readable by the NFS anonymous user (the current controller
requires a world-readable source file inside a private 0700 parent directory);
keep the export on a trusted network. The export directory and image must
be on the same filesystem for the hard link.
The
claim server signs only after persisting consumption. Keep the foreground
service running after a claim until the guest's terminal result is observed:
the writer still needs NFS for the subsequent transfer and readback. Stop the
service manually afterward. A started service cannot be restarted or rearmed
from the same state, including after an interrupted or lost acknowledgement;
inspect the target and create a separately reviewed new job if needed.

These commands are commissioning components, not a one-command printer flash.
The SD boot artifact must contain the same signed job, verifier and exact NFS
endpoint. No automatic trigger or automatic return to eMMC boot is provisioned.
The QEMU harness exercises the synthetic path; the host-service NFS-Ganesha
configuration has not yet been tested against a physical printer.
Offline unit tests use synthetic keys to send a real HTTP claim over loopback,
verify its Ed25519 receipt, and confirm that replay returns `409 CONSUMED`.
An isolated Beelink Ganesha 4.3 startup test parsed the generated config and
opened the configured NFS listener; it did not exercise printer access or the
read-only client ACL. The config uses an unquoted bind IP and an explicit idmap
file, as required by that tested package.
The export defaults, per-client override and listener address follow the
[NFS-Ganesha export configuration](https://github.com/nfs-ganesha/nfs-ganesha/blob/next/src/doc/man/ganesha-export-config.rst)
and [core configuration](https://github.com/nfs-ganesha/nfs-ganesha/blob/next/src/doc/man/ganesha-core-config.rst)
(upstream `next`, accessed 2026-09-27). The executable version used in a
physical session must be recorded separately; this source citation is design
provenance, not compatibility evidence.
