# Write the spare eMMC on Windows, Linux or macOS

These instructions write the private test-sv08-01 host image to the owner's
blank nominal 32 GB eMMC through a USB reader. Keep the factory module unchanged
for host rollback. The image passed offline checks; physical boot and reader/module
compatibility remain unverified. No ST-Link connection is needed for this step.

Use [balenaEtcher](https://etcher.balena.io/) for the graphical writing and
validation workflow on all three operating systems. Its
[image-support checks](https://etcher-docs.balena.io/MANUAL-TESTING/#image-support)
include XZ-compressed images, so the `.img.xz` can be selected directly.
Both sources accessed 2026-09-05; the platform procedures below have not yet
been exercised with this project's image on a physical reader.

## Obtain and check the image

Transfer these files from the build workstation's private `artifacts/` directory
to a local folder on the computer that will run the USB writer:

- `test-sv08-01-host-v1.img.xz`
- `test-sv08-01-host-v1.img.xz.sha256`

The image is private and is not included in a Git clone or GitHub download.
The compressed file is 291,106,052 bytes (about 278 MiB); its SHA-256 is:

```text
0fbcf1fe7b8418609ddf5d6c9b3946106762624ccebe154c57923e17cd479211
```

Use the platform-specific checksum command below before writing. If it does not
match, stop and transfer the file again. The destination needs at least
8,589,934,592 bytes (8 GiB), regardless of the compressed download size.
Keep the image file on the computer's storage, not on the eMMC being written.

## Windows

1. Install the Windows version from the official Etcher website linked above.
2. Open PowerShell in the folder containing the downloaded image and run:

   ```powershell
   Get-FileHash .\test-sv08-01-host-v1.img.xz -Algorithm SHA256
   ```

   Compare the result with the hash above; uppercase/lowercase does not matter.
3. With the USB reader unplugged, fit the blank spare in the correct orientation,
   then attach the reader to Windows. Cancel any request to initialize or format
   the module. There is no need to format it before flashing.
4. Follow [Write and validate](#write-and-validate) below. Accept the Windows
   administrator prompt when Etcher starts writing.
5. After successful validation, use **Safely Remove Hardware** if the reader is
   still mounted, then unplug it. Cancel any further Windows format prompts.

## Linux desktop

1. Install the Linux package appropriate for your distribution and architecture
   from the official Etcher website linked above.
2. Open a terminal in the image/checksum folder and run:

   ```sh
   sha256sum -c test-sv08-01-host-v1.img.xz.sha256
   ```

   Continue only if it reports `test-sv08-01-host-v1.img.xz: OK` and exits zero.
3. Run the following read-only inventory before and after attaching the USB
   reader with the blank spare fitted. Match the newly attached whole device
   by its model, size and USB transport; device names can change between uses.

   ```sh
   lsblk -b -o NAME,PATH,TYPE,SIZE,MODEL,TRAN,MOUNTPOINTS
   ```

4. Close file-manager windows using the module and unmount any automatically
   mounted partitions through the desktop's disk utility. Follow
   [Write and validate](#write-and-validate), supplying administrator
   authentication when requested.
5. After successful validation, use the desktop's safely remove/eject action
   for the reader before unplugging it.

## macOS

1. Install the macOS version from the official Etcher website linked above,
   choosing the download appropriate for your Mac if architecture options appear.
2. Open Terminal in the image/checksum folder and run:

   ```sh
   shasum -a 256 -c test-sv08-01-host-v1.img.xz.sha256
   ```

   Continue only if it reports `test-sv08-01-host-v1.img.xz: OK` and exits zero.
3. With the USB reader unplugged, fit the blank spare, then connect the reader.
   If macOS says the disk is unreadable, choose **Ignore**, not **Initialize**.
   Compare this read-only inventory before and after connection to identify the
   external whole disk and its capacity:

   ```sh
   diskutil list external physical
   ```

4. Follow [Write and validate](#write-and-validate), granting the requested disk
   access and administrator authentication. Do not erase or partition the module
   in Disk Utility first.
5. After successful validation, eject any still-mounted eMMC volumes in Finder
   or eject the identified external device in Disk Utility, then unplug the reader.
   Ignore unreadable-disk prompts caused by the Linux filesystem.

## Write and validate

**Flashing overwrites the selected device. Select the blank spare, never the
retained factory module or a computer disk.**

1. In Etcher, choose **Flash from file** and select `test-sv08-01-host-v1.img.xz`.
2. Choose **Select target**. Check the reader identity and spare capacity against
   the device you just connected; review the target even if selected automatically.
3. Choose **Flash!** and leave the reader connected through writing and validation.
4. Continue only after validation succeeds. If either stage fails, retain the
   error details and resolve the failure before installing the module.

If the reader is missing or reports zero/incorrect capacity, stop and check its
connection and module compatibility. Do not select another disk to continue.
A USB reader need not expose a drive letter or a readable Linux filesystem to
be a whole-device writing target. Leave the remaining space on the 32 GB spare
unallocated; expansion is a later recorded operation.

## Install and test the spare

Cleanly shut down the idle printer with heater targets zero, disconnect power,
then remove and label the factory module. Fit the spare with its verified
orientation, connect Ethernet and power on. Find `sv08-mainline` in the router's
DHCP lease list; its address may differ from the factory host.

Follow the [first-boot checks](test-sv08-01-image.md#artifact-and-first-boot) and
record the writer version, reader/module models, validation result and boot
observations in private local evidence. SSH uses `sovol` and the previously
authorized key, which may only be available on the build workstation. There is
no password login, Wi-Fi configuration, printer web interface or active printer
service in this host candidate. Do not flash MCUs or command heat/motion for this
test. If boot fails, disconnect power before swapping the original module back.
