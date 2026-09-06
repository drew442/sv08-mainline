# Make an image file from an eMMC module

Use this offline procedure to preserve the current state of test-sv08-01's new
module, or optionally its retained factory module. On 2026-09-06 the owner
reported that the new image booted on the new eMMC; a backup of that installed
system and a restore test have not yet been reported. These capture instructions
are prepared guidance, not a hardware-tested backup procedure.

## Prepare the source and destination

1. Confirm the printer is idle and heater targets are zero. Cleanly shut down
   the host (`sudo systemctl poweroff` on the identified printer), wait for
   shutdown, disconnect power, and only then remove the module. Never image the
   mounted, running root filesystem as though it were a consistent backup.
2. Label which module you are capturing: the new nominal 32 GB module or the
   retained factory module. Record model/markings, board revision if known,
   reader model, date, computer OS, tool version and exact source capacity.
3. Fit the module to the unplugged USB reader, then attach it to the capture
   computer. Cancel format, initialize, repair and erase prompts. Keep source
   volumes unmounted during reads; close Explorer/Finder/file-manager windows
   using them. A reader with hardware write blocking can provide extra protection.
4. Use a new private directory on a different disk for the output. In this
   repository, use ignored `backups/test-sv08-01/` with a unique capture subdirectory.
   Allow space for two full reads: over 64 GB free is sensible for a nominal 32 GB
   module. The destination filesystem must support files over 4 GiB; FAT32 does not.

A full capture includes the **whole exposed device**, including its partition
table, bootloader area, partitions and unused space. Expect approximately the
module's full capacity, not the 8 GiB size of the original installer. Measure
exact bytes; do not assume all nominal 32 GB modules have identical capacity.
Do not shrink partitions or trim the capture as part of this backup.

## Windows: Win32 Disk Imager

Use [Win32 Disk Imager from its SourceForge project](https://sourceforge.net/projects/win32diskimager/)
(accessed 2026-09-06), which supports reading removable devices into raw image
files. This operation is **Read**, not Write; the Etcher flashing workflow in
our other guide is for the opposite direction.

1. Use Disk Management to match the reader, whole disk capacity and its boot
   volume's drive letter. For exact bytes, use this read-only PowerShell inventory:

   ```powershell
   Get-Disk | Select-Object Number, FriendlyName, SerialNumber, BusType, Size
   ```

2. Run Win32 Disk Imager as administrator. Set **Image File** to a new filename
   such as `D:\SV08-backups\2026-09-06-new-emmc\emmc.img` in an existing private
   folder. Select the source module's drive letter under **Device**, confirming
   its association with the whole physical disk. Do not select another drive
   if the reader is absent; do not format the module to make it appear.
3. Leave **Read Only Allocated Partitions** unchecked if offered. That option
   stops at the partition boundary and is not a full-device capture. Click
   **Read** and wait for successful completion; retain errors if it fails.
4. Repeat **Read** into a different new file, `emmc-second.img`, without booting
   or modifying the source between reads. Close any automatically opened volumes
   between captures; if the reads differ, investigate possible host writes.
5. In PowerShell in the backup folder, check both lengths and hashes:

   ```powershell
   Get-Item .\emmc.img, .\emmc-second.img | Select-Object Name, Length
   Get-FileHash .\emmc.img, .\emmc-second.img -Algorithm SHA256 |
       Format-List Path, Hash
   ```

Both lengths must equal the recorded **whole disk** byte count, and both SHA-256
values must match. Save the results privately. The allocated-partition option
is described in the project's [1.0 README, mirrored here](https://github.com/znone/Win32DiskImager/blob/master/README.txt)
(accessed 2026-09-06). A small image is not a full capture merely because the read
operation completed.

## Linux: read the whole device with GNU dd

Disable desktop automount before connection where possible. Compare the inventory
before and after attachment, identifying the reader by topology, model and capacity:

```sh
lsblk -b -o NAME,PATH,TYPE,SIZE,MODEL,SERIAL,TRAN,MOUNTPOINTS
findmnt
swapon --show
```

Unmount all source partitions through the disk utility or `umount` on each
identified mount. If any source partition is used as swap or another active
storage layer, stop and resolve that use first. Never unmount the capture
computer's own system disk to proceed.

In a new backup directory on separate storage, set `SOURCE` to the reviewed
**whole device**, not a partition. The placeholder below is intentionally invalid.
Run commands one at a time, continuing only on success:

```sh
SOURCE=/dev/REPLACE_WITH_REVIEWED_EMMC
sudo blockdev --getsize64 "$SOURCE"
df -B1 .
umask 077
sudo dd if="$SOURCE" of=emmc.img bs=4M iflag=fullblock oflag=excl status=progress
sudo dd if="$SOURCE" of=emmc-second.img bs=4M iflag=fullblock oflag=excl status=progress
stat -c '%n %s' emmc.img emmc-second.img
sudo cmp emmc.img emmc-second.img
sudo sha256sum emmc.img emmc-second.img > SHA256SUMS
```

`if=` is the source device; `of=` is a new regular file in your backup directory.
`oflag=excl` refuses an existing output. Do not add `conv=noerror` or padding
options to hide read failures. Both lengths must equal `blockdev`'s byte count,
`cmp` must exit zero, and the two saved hashes must match. Files created by sudo
may require sudo for later reads or a deliberate ownership change on those backup
files. GNU's [dd manual](https://www.gnu.org/software/coreutils/manual/html_node/dd-invocation.html)
documents these options (accessed 2026-09-06).

## macOS: read the whole device with dd

Use Terminal to identify the newly attached external physical disk:

```sh
diskutil list external physical
diskutil info /dev/diskN
```

Replace `N` with the reviewed reader's disk number throughout; do not use a
partition suffix such as `s1`. Record the exact byte count shown by `diskutil info`.
Ignore unreadable-disk prompts. In a new private backup directory on separate
storage, unmount the source's volumes, then capture it twice:

```sh
diskutil unmountDisk /dev/diskN
df -k .
umask 077
set -C
sudo dd if=/dev/rdiskN bs=4m > emmc.img
sudo dd if=/dev/rdiskN bs=4m > emmc-second.img
stat -f '%N %z' emmc.img emmc-second.img
cmp emmc.img emmc-second.img
shasum -a 256 emmc.img emmc-second.img > SHA256SUMS
```

Run each command only after the preceding one succeeds. `set -C` prevents shell
redirection from overwriting existing output files; keep it enabled for both
reads. `/dev/rdiskN` is the raw interface to the same identified whole disk.
There is no `of=` device here: stdout goes to a new image file. Press **Control-T**
for progress on macOS while `dd` runs; do not interrupt a successful read.
Both file lengths must match the recorded device bytes, `cmp` must exit zero,
and hashes must match. Apple's [dd manual source](https://github.com/apple-oss-distributions/file_cmds/blob/main/dd/dd.1)
was checked on 2026-09-06. After verification, eject the identified source:

```sh
diskutil eject /dev/diskN
```

## Accept, store and restore

Keep the capture only as complete when both reads succeeded without errors,
both sizes equal the exposed device capacity, and hashes match. On Windows/Linux,
safely eject the source after verification. A second read on the same destination
disk is not a separate storage copy: copy the image and checksum record to another
private disk and check its hash again. Compression is optional after verification;
retain the raw-image hash and verify decompression before relying on a compressed
copy. A post-boot backup will differ from the installer because the system has
written host keys, machine identity, logs and other state.

Record source identity/capacity, regions, timestamps, OS/tool versions, commands,
errors, file sizes, SHA-256 values and repeat-read results in the private backup
inventory. Images of a used module contain SSH private host keys, accounts and
potential credentials; keep them out of Git and public downloads.

A USB whole-device image usually covers only the eMMC **user area**. It does not
capture separately addressed boot0/boot1 regions, EXT_CSD settings, RPMB, or either
printer MCU. Record what the reader exposes and retain any separate region/metadata
captures. See the [recovery plan](test-sv08-01-recovery.md) and
[Linux MMC partition documentation](https://cdn.kernel.org/doc/html/latest/driver-api/mmc/mmc-dev-parts.html)
(accessed 2026-09-06). The original module's recorded zero boot regions are not
measurements of the new module.

For restoration, use the [flashing guide](flashing-emmc.md) with **your backup
filename and its checksum**, rather than the installer's filename/hash. The
replacement must be at least as large in exact bytes as the complete raw backup,
even if both modules are sold as 32 GB. Validate the write and demonstrate boot
on the identified replacement before claiming recovery verified. Keep the factory
module unchanged; a host backup does not restore altered MCU firmware.
