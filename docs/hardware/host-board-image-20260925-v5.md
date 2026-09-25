# Board diagnostic image v5 write and readback

This is an offline-reviewed and physically written diagnostic image for the
reported stock `H616_JC_6Z_V1.2` board. It is not a printer release: its
manifest keeps `deployable` and `physical_boot` false. The v5 JSON file records
all component and image hashes; the raw image is 7,818,182,656 bytes with SHA-256
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.

An independent GPT-5.6-Sol medium review on 2026-09-25 passed the offline byte
checks for that exact image. It validated the GPT and all six partition ranges,
read-only filesystem checks, SPL/U-Boot environment records, and the matching
root A/B contents. Both boot partitions' initramfs contain the persistent-data
hook omitted from v4; their hook embeds the data partition's recorded PARTUUID.
The compressed image also passes `xz -t` and expands to the recorded raw-image
size and hash.

On 2026-09-25, the reviewed image was written to the spare eMMC through the
05e3:0747 USB writer. The live target matched the previous v4 spare's disk GUID,
six PARTUUIDs, and loader hash. The exclusive whole-device write covered exactly
7,818,182,656 bytes; streaming hash, `fsync`, and device flush passed. A full
direct-I/O readback of 1,864 × 4 MiB matched the raw image SHA-256 exactly. The
kernel reports the six expected partition sizes and PARTUUIDs, with all target
partitions unmounted. The private writer receipt is retained on Beelink at
`/home/drew/sv08-captures/board-v5-write-20260925/write-receipt.json`.
After readback and partition checks, the USB reader was safely powered off with
`udisksctl power-off`; it disappeared from Beelink's USB and block-device lists.

`sgdisk -v` reports that the secondary GPT header is not at the physical 32 GB
device end. This is expected: the image intentionally preserves the 8 GB disk
footprint, with the backup GPT at the end of that image. It was not relocated or
expanded. The spare has not yet been booted with v5. V4's exact prepare exception
was not captured; the missing initramfs hook is a strong, reproduced candidate
cause, not a measured device-side exception. Physical DRAM stability, Wi-Fi,
display/touch behavior, printer outputs, heat, motion, and printing remain
unverified.
