# v5 image GPT identity audit

Date: 2026-09-27. This read-only audit checked the v5 compressed artifact on
Beelink and its private USB-writer receipt. The compressed SHA-256 and size
match the receipt. Streaming decompression produced exactly 7,818,182,656 bytes;
the raw image SHA-256 matches both the recorded write hash and direct readback
hash. The temporary decompressed file was removed after inspection.

The image itself has disk GUID
`b643a41a-d63f-40aa-9940-74a8f4e19a8d`. Its six GPT records are:

| # | Partition | Byte offset | Size | PARTUUID |
| --- | --- | ---: | ---: | --- |
| 1 | boot-a | 16,777,216 | 201,326,592 | `ba55a9b4-7969-423b-a739-db62e231b7a1` |
| 2 | root-a | 218,103,808 | 2,147,483,648 | `26c68198-9248-47af-bbd3-643f1b604ef5` |
| 3 | boot-b | 2,365,587,456 | 201,326,592 | `7b6e5211-6c5f-432f-9afc-2ac7e4f80b04` |
| 4 | root-b | 2,566,914,048 | 2,147,483,648 | `d8d04a9a-f51f-41b3-a474-e079efe97186` |
| 5 | recovery | 4,714,397,696 | 536,870,912 | `b28438ed-f895-4b93-9bad-d27d3890ccd3` |
| 6 | data | 5,251,268,608 | 2,565,865,472 | `4773f966-0678-4cf5-bb83-8ee6fb11d8eb` |

`sgdisk -v` found no GPT problems and reported an unusual gap between primary
GPT metadata at LBA 1 and the partition entry array at LBA 4096. The audit
preserves this layout and does not repair or rewrite the image.

The private receipt also contains a different GUID. The retained one-shot writer
script confirms that this value is the expected *destination disk GUID before
the write*, checked by `verify_target()`. It is not the image's disk GUID. The
raw image has the `b643…` GUID above; a whole-device write replaces the prior
target GPT. The two identifiers have different roles and are expected to
differ. The prior target GUID is omitted from the public record.

The [machine-readable audit record](host-board-image-20260925-v5-gpt-audit-20260927.json)
binds the image hash, disk GUID, partition records, receipt hash, and writer
script hash. The receipt and writer script remain private on Beelink. This
proves image-file provenance only; it does not identify the currently installed
eMMC, demonstrate printer boot, or authorize a write. The H616 candidate builder
remains physically disabled while its image allowlist and boot/claim trust path
await independent review.
