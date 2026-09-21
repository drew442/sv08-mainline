# Corrected candidate resource measurements

These values are from candidate `recovery-composition-candidate-export-rebuilt-1dca3f7`, whose
`recovery.ext4` SHA256 is
`4b8b4869d5059d424379c32fb3d9b10b15558fedb8b966966d6fdaf797080c52`.

| Item | Measurement |
| --- | ---: |
| Recovery image size | 536,870,912 bytes (512 MiB) |
| Allocated ext4 blocks | 327,692,288 bytes |
| ext4 block count | 131,072 |
| ext4 free blocks | 49,081 |
| ext4 inode count | 32,768 |
| ext4 free inodes | 30,017 |
| SquashFS `/usr` | 241,356,800 bytes |
| Source inventory | 20,451 files / 899,801,608 bytes |
| Peak QEMU RSS | 2,136,940,544 bytes (cleanup-failure run; archive-corruption run 2,112,851,968 bytes) |
| Candidate build record SHA256 | `363fda0dea64a8ca4d3268ce17c18e2f9228b17423fb8e04670c5d079b762595` |

The accepted factory-sized layout is 7,818,182,656 bytes, recorded by the
source-backed board image evidence in `docs/hardware/host-board-image-20260915-v2.json`.
The corrected recovery image remains exactly 512 MiB; physical GPT layout and eMMC
capacity are not written or boot-tested by this offline feature.

Hash-bound result records:

- keyboard: `3418e34e72702a9836d4e0a5aa50e564bd0fb86ce434ae318a6c959864181a19`
- touch: `dcee90d92dd5aafc1b18053218f8b987d217ec14551f046948c4c7fc94e87fc8`
- keyboard-plus-mouse: `5547b7183411ea1ae41d697034bbf39184d8c2618ca40e3fecaf056fd233150f`
- source read-only control: `33e92be27d08b0ccdfa2f27c1bce318b75332c45bcba9d1d62b2490704a5c0dd`
- wrong provider: `cb2705355ebc62371f4ef3ccb39d9539ce4eca32b8565532b9243c147f6c4bcf`
- destination removal: `5105fad2a4bf49e777244d6fda43447747afb6f972c129bb8c87d37134532af8`
- no space: `5b2964234ea3b68c64dc5c13f165704e7d13d6cd6de04674df320a69dcb4ba8e`
- archive corruption: `dddc052ad5ea4c86a12f77926af8776966060661d43863e872da89c1292f2d55`
- operation-owned cleanup failure: `bdf8baea2c38e51dab6c9613e9d42510299b1d5421e80606a2b91c632ffe7c42`

Preparation and export workspace are disposable per-run output directories. Their
largest retained positive result is approximately 224 MiB, and the candidate build
workspace peaked at approximately 1.6 GiB including the source assembly and image.
The final package/module/code delta and a physical factory-layout write remain
release evidence, not claims made by this offline run.
