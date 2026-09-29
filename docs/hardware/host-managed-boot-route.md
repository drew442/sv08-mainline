# Managed SD/eMMC boot routing

2026-09-29; test-sv08-01, owner-reported H616_JC_6Z_V1.2. This is an offline
prepared diagnostic route toward [H12](coordinated-human-tasks.md), with physical
boot/reset/MMC routing still pending. The [approval](../features/sd-managed-boot-route/record.json)
and [source audit](host-managed-boot-route-research-20260929.md) define its bounds.
The running SD root, GUI and SSH have separate [H13 evidence](host-sd-recovery-host-first-boot-20260929.md).
No physical media operation is implied by these commands.

## Main-loader preparation

The [command fragment](../../configs/host-os/sv08-managed-boot.fragment) enables
CMD_HASH, HASH_VERIFY and CRC32_VERIFY through upstream Kconfig. The coordinator
copies the retained pinned build into isolated scratch, keeps its toolchain,
patches, BL31, default environment and reproducible epoch, applies that fragment,
runs olddefconfig and builds main U-Boot. The effective diff admits those three
options, with CONFIG_HASH only if the pinned CMD_HASH selection requires it.
Any other drift stops preparation. No upstream or historical receipt is edited.

The [assembler](../../scripts/sd_boot_route.py) requires the exact old loader/config
hashes and 40,960-byte SPL boundary. It parses both FITs, compares extracted
BL31/board DT hashes and boot configuration/load-address properties, checks the
unchanged compiled environment in the ELF and deployed main stage, and requires
linked hash/crc32 commands. It applies the pinned upstream binary conversion
(`aarch64-linux-gnu-objcopy --gap-fill=0xff -R .hash -O binary`) and requires the
result to equal the FIT's main-stage data. Fresh regular outputs contain the old
SPL plus the new FIT, and a receipt hashes every input. The receipt labels the
new artifact physically unvalidated.

For the supplied public build bundle in `local/managed-boot-inputs`:

```sh
python3 scripts/sd_boot_route.py prepare \
  --old-loader local/managed-boot-inputs/old-loader.bin \
  --old-config local/managed-boot-inputs/old.config \
  --new-config local/managed-boot-inputs/new.config \
  --new-fit local/managed-boot-inputs/new.fit \
  --elf local/managed-boot-inputs/new.elf \
  --environment local/managed-boot-inputs/default.env \
  --old-provenance local/managed-boot-inputs/old-provenance.json \
  --new-provenance local/managed-boot-inputs/new-provenance.json \
  --output local/managed-loader.bin --receipt local/managed-loader.json
```

Old/new provenance has identical `config` source/patch manifest and `compiler`,
plus `artifacts.bl31.bin.sha256`. New provenance separately binds
`effective_config_sha256` and `base_provenance_sha256`; the source manifest is
not a claim that the effective configs are identical. Build dependencies are
Python 3, nm, ARM64 GNU objcopy and the retained U-Boot inputs. No build/install
or source-download command runs from this assembler.

The actual assembled loader is 786,225 bytes, SHA-256
`350a941a7ec67b541308d235bffa4b937b8171f683f3e96b0c51dd32fab64544`.
The new effective config SHA is
`6acb5de178be927a6c0cd71f906f5cf51f23a7ae2d2d87e880e33849536857bf`.
The coordinator measured 319,037,904 logical bytes / 417 MiB allocated scratch,
within the 512 MiB budget. Assembly has only bounded small-file scratch; loader,
preimage, receipts and captures must stay below the separate 64 MiB bound.

## SD inspection and separately reviewed transfer

Coordinator-owned private policy fields are `device`, `dev_t`, `controller`,
`cid`, `capacity`, `root_dev_t`, `boot_dev_t`, `image_bytes`, `disk_guid`,
`partitions`, `loader_sha256`, `receipt_sha256`, `preimage_sha256`,
`capture_and_users_released:true` and `ownership_lock`. `partitions` uses the
existing GPT inspector's records: number/name/partuuid/offset_bytes/size_bytes.
Bind these to a fresh named SD intake and the exact prepared receipt, rather than
copying a device name or borrowing an eMMC policy. Keep all device identifiers
and policy in ignored private paths.

The admitted card's [actual p1](host-sd-recovery-host-write-20260929.md) begins at
16 MiB; p2 is 512 MiB at byte 150,994,944. Backup GPT is at the prepared image's
738,197,504-byte end, not the full card's end. The absolute write limit remains
`8192 + loader_bytes <= 1048576`, regardless of partition spacing.

```sh
sudo python3 scripts/sd_boot_route.py sd \
  --device /dev/REVIEWED_SD --loader local/managed-loader.bin \
  --receipt local/managed-loader.json --policy local/reviewed-sd-policy.json \
  --preimage local/reviewed-loader-span.bin
```

Without `--apply`, this opens SD O_RDONLY and reports admission/preservation
hashes without writing SD. The coordinator retains the complete exact-length
span at byte 8192 as a fresh regular preimage, plus the original SD image, before
reviewing any transfer. Adding `--apply` is the separate physical transfer after
immediate independent review and applicable owner authorization. Capture stdout
and stderr with the reviewed invocation as its operation receipt.

Production admission requires a whole SD block descriptor with exact
controller/CID/dev_t/capacity, reviewed CRC-valid GPT and partition identities,
sole ext4 root mounted `ro,norecovery`, root partition BLKROGET=1, boot partition
unmounted, no holders, no competing block descriptors and no competing SD mount
in visible process mount namespaces. A stable cooperating-controller lock and
whole-device flock provide **advisory ownership**; they do not provide O_EXCL or
protect against an uncooperative privileged writer. Release other consumers and
keep that limitation in the physical review.

The write descriptor is compared with the admitted readonly descriptor and all
admission/preimage checks run again at the boundary. MBR, both GPT headers and
arrays, and full FAT/root ranges are derived from that admitted descriptor and
hashed in 1 MiB chunks before/after; no card/image copy or FAT change occurs.
One pwrite addresses only the loader span, then fsync, BLKFLSBUF and exact
readback. Partial write, flush, changed identity/mount or uncertain readback
stops without retry or rollback. Preserve the original preimage and failed
operation output for a separately reviewed USB recovery; do not rerun blindly.

## Explicit serial route

The [controller](../../scripts/sv08_serial_boot_route.py) binds the existing script:
1075 bytes, SHA-256
`ce18bf74e3d8ae840bfb90129ba28515ba89cbd2759bc32ecd0418f6987d1ddd`,
root PARTUUID `deaf981d-7441-428c-bf43-ce40bca6ca65`, envelope
`e70601624c206ab0cea69e7ce142e7adeeb0faff13eee5e3fcf545bc08898fa1`.
The supplied boot.cmd must equal the existing builder's script, preserving all
three payload SHA checks, initrd length and fixed boot arguments. SHA verification
is required before sourcing; no payload/script/FAT file is changed.

Private serial policy binds `device`, `dev_t`, exact resolved `sysfs_path` and
`ownership_lock`, with `capture_released:true`, `fresh_environment_reviewed:true`
and `mmc_mapping_reviewed:true`. The fixed CH340 VID/PID is only an additional
check; it cannot identify the intended bridge without its private topology.
The cooperating receive-only collector must release its descriptor and share
this lock. Existing competing descriptors refuse admission; TIOCEXCL excludes
later opens. The serial port must already be raw 115200 8N1/CLOCAL without
HUPCL or hardware flow control. The controller changes no termios/control lines.

```sh
python3 scripts/sv08_serial_boot_route.py --route sd \
  --policy local/reviewed-serial-policy.json \
  --script local/managed-boot-inputs/boot.scr \
  --command local/managed-boot-inputs/boot.cmd \
  --composition local/managed-boot-inputs/composition.json \
  --capture local/managed-serial.raw
```

The default only inspects the supplied inputs. After separate reviewed reboot
preparation and capture arbitration, `--apply` waits for recognized U-Boot
countdown before sending one space. At recognized `=> ` prompts it sends only
mmc dev 0, mmc info, fatload of mmc0:1 boot.scr, hash sha256 and source, checking
command echoes, SD type, exact loaded count and exact SHA result. Transmission
stops after source; no Linux command, reset, arbitrary interpolation or retry is
available. Timeout, unexpected prompt/output/hash/identity stops the sequence.
Capture is bounded to 1 MiB with 15-second gates and retained even on refusal.

`--route emmc` sends zero bytes and releases standard autoboot. It does not
implement new A/B policy. Immediately before the coordinator's separately
reviewed reboot, bind the exact fresh redundant environment and the expected
A-attempt decrement if SD interception is missed. Linux MMC numbering cannot
establish the U-Boot mapping. Physical mapping and one new-loader SD-return
probe remain gates before accepted p5 staging/writer handoff. RTC/time correction
and new signed-job preparation have their own H12 gates.

## Writer success return and offline checks

Only the existing production C `finish` changed: compile-time
SV08_H616_RECOVERY_HANDOFF plus exact `PASS` requests RB_AUTOBOOT. All other
statuses/builds retain RB_POWER_OFF, including CLAIM_ONLY_PASS, final-environment
failures and PASS lookalikes. A returned reboot proceeds to pause forever, with
no retry/new target open. The sole PASS remains after full final readback/hash;
claims, admission, marker consumption and environment-last transfer are unchanged.

```sh
python3 -m unittest tests.test_sd_boot_route tests.test_sv08_serial_boot_route \
  tests.test_h616_reimage_candidate.ManagedFinalizerTests -v
```

36 checks passed with supplied public artifacts: real bounded regular-file
writes and partial/flush/readback/preservation faults, admission races and
sysfs/mount fixtures, exact-loader assembly, fragmented serial/refusal transcripts,
native captured production-finalizer syscalls and ARM64 finalizer compilation.
Optional actual-input tests explicitly skip if that coordinator bundle is absent.
No test opens a production media or serial target. Compatible pinned sandbox
hash/crc32 good/corrupt semantics are separate coordinator evidence; silent `-v`
success must never be confused with lack of verification.

For small QMP integration, call `compile_finalizer_harness` in
[the focused test module](../../tests/test_h616_reimage_candidate.py) with
`handoff=True,capture=False,compiler='aarch64-linux-gnu-gcc',static=True` and fixed
status PASS or FAILED_FINAL_ENV. Package its resulting executable as PID1 `/init`
in a tiny disposable initramfs; run the assigned ARM64 kernel without NIC/block
media and stop QEMU at the first guest event. This harness includes the actual C
finish, with test syscall replacements only when capture=True; no production
hooks were added. It never calls the retained writer main.

Coordinator integration observed guest RESET for PASS and guest SHUTDOWN for
FAILED_FINAL_ENV using Debian 6.12.107 ARM64, kernel SHA
`9c37ace54ef7e1919411fd912e9f34d6982ddd7f4c8ef3c8aee56f4c4d70db67`;
result SHA `ec568c7b55624a3accec0655cdeaf2d83b5cf7e727ac67063eede04e2f8a2ddd`.
This establishes Linux/QEMU finalizer behavior, not H616 reset or boot routing.
Reuse unchanged bulk-write/second-boot evidence at its stated scope; the physical
full-write review must bind the newly built actual writer hash and normal return
loader/environment. Physical H12 write/automatic return and independent feature
verification remain required. Retirement: supported recovery boot selection.
