# Board diagnostic image v5 byte review

This is an offline-reviewed diagnostic candidate for the reported stock
`H616_JC_6Z_V1.2` board. It is not a printer release: its manifest keeps
`deployable`, `physical_write`, and `physical_boot` false. The v5 JSON file
records all component and image hashes; the raw image is 7,818,182,656 bytes
with SHA-256
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.

An independent GPT-5.6-Sol medium review on 2026-09-25 passed the offline byte
checks for that exact image. It validated the GPT and all six partition ranges,
read-only filesystem checks, SPL/U-Boot environment records, and the matching
root A/B contents. Both boot partitions' initramfs contain the persistent-data
hook omitted from v4; their hook embeds the data partition's recorded PARTUUID.
The compressed image also passes `xz -t` and expands to the recorded raw-image
size and hash.

That review only establishes the identity and offline consistency of the
candidate bytes. It does not approve or establish an eMMC write, readback, or
physical boot. Those remain separate commissioning steps. V4's exact prepare
exception was not captured; the missing initramfs hook is a strong, reproduced
candidate cause, not a measured device-side exception. Physical DRAM stability,
Wi-Fi, display/touch behavior, printer outputs, heat, motion, and printing
remain unverified.
