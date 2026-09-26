# QEMU eMMC writer descriptor binding: offline validation

Date: 2026-09-26 UTC. Feature: [network-emmc-fd-binding](../features/network-emmc-fd-binding/proposal.md).
Status: native, static ARM64, and disposable QEMU integration checks passed. No printer or physical block device was contacted.

The disposable [QEMU writer](../../tests/fixtures/sd-network-root/emmc_image_writer.c) now checks the already opened `/dev/sda` block descriptor's `st_rdev` against the strictly parsed, newline-terminated major/minor in `/sys/block/sda/dev` before its first write. Missing, malformed, truncated, oversized, mismatched, or non-block identity refuses the operation. The existing serial, capacity, source, and claim checks remain. The descriptor stays open for writing, flush, and full readback, including the injected readback fault. The writer seeks that descriptor to offset zero after flushing; it never resolves the target path again for verification.

Native synthetic metadata tests cover matching and changed major/minor, malformed and truncated attributes, overflow, extra data, and a non-block descriptor. A source-structure check confirms one target open, the identity check before writing, and the retained descriptor in both readback paths. These checks do not simulate a real device being unplugged or a real eMMC CID.

| Check | Evidence at this revision |
| --- | --- |
| `nfb-01` | Native synthetic block `st_rdev`/sysfs comparison and source ordering pass. |
| `nfb-02` | Source-structure check and strict ARM64 static build pass. The writer uses one opened block descriptor for target identity, write, flush, and full readback. The fault-injection readback path also retains that descriptor. |
| `nfb-03` | Disposable QEMU run-002 completed a full 7,818,182,656-byte write and readback. Independent host readback SHA-256: `7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`. The 32,000,000,000-byte virtual target identified as `SV08_QEMU_REIMAGE_TEST_ONLY`; both GPT CRCs, disk GUID, and all six partition records were checked. Claim consumption preceded writing. |
| `nfb-04` | 31 relevant Python/native tests and strict static ARM64 compilation pass. Four fresh QEMU fault runs also pass: before-write preserved the target, while partial-write, flush, and readback faults confirmed a modified source-matching prefix, no success receipt, and HTTP 409 on claim replay. Independent delivery review remains with the coordinator. |

The disposable QEMU integration used QEMU 8.2.2, ARM GCC 13.3.0, sgdisk 1.0.10, and the Beelink host kernel `7.0.0-31-generic`. The full run took 2,586.48 seconds. It emitted 12 guest `GFP_ATOMIC` warnings; it had no OOM or NFS error. The full-transfer receipt SHA-256 is `37c551fe91534d2914047ea5b56648c2490b5f61d7d51765eb0eeb0b44979cda`.

Storage accounting after the six disposable attempts (including the inconclusive run-001) showed 7,818,182,656-byte source files and 32,000,000,000-byte virtual targets, all sparse regular files. The retained `/tmp/sv08-qemu-fd-binding` run directory occupied 8,077,312 allocated bytes at measurement; `df -B1 /tmp` reported 10,756,775,936 bytes available on Beelink. Peak filesystem consumption during the runs was not captured, so the post-run allocation/free-space values must not be read as peak-use measurements. Run-002's target alone had 1,970,176 allocated bytes for its 32,000,000,000-byte apparent size.

Fresh injected-fault receipts are: readback `06b26e67005155a97b4d4e183c9fe35a48c1552d4820a5dd4e68816ec8323e94`; before-write `24d449c2b26dd5e4b394a1afd6a91be0372e8e230c3e0e40499f448361ea03bc`; partial-write `fc98af545cf33538c77422f982665a6ebe7546928320bcc63c37f50e603d6597`; and flush `c52610431a62cce499a0fe75d55c1d292f27579a27b4a5af4dba6000e9413abc`. The receipt files were copied from Beelink scratch and their hashes checked locally. An earlier full-run attempt was stopped prematurely when serial output paused; it is retained as inconclusive and is superseded by the successful run-002.

Commands run in the isolated feature worktree:

```sh
PYTHONPATH=tests python3 -m unittest test_sd_network_emmc_write test_emmc_job test_sd_network_env_probe test_sd_network_image -q
PYTHONPATH=tests python3 -m unittest test_sd_network_cid_admission -q
aarch64-linux-gnu-gcc -static -O2 -Wall -Wextra -Werror -Wno-unused-function tests/fixtures/sd-network-root/emmc_image_writer.c -o /tmp/sv08-emmc-fd-binding-writer-arm64
git diff --check
```

The four-module command passed 31 tests; the CID-admission command passed 3 tests. Strict static ARM64 compilation and report relative-link validation passed. The writer source SHA-256 is `b31cd1a724e841e3a97b7096b82491220bd11737a8d6b38f5997d3e5425ae3b8`; focused test source SHA-256 is `fe112c074723f783a316b8fe3895c8afa3f754557b1f767f7f0a21ea09f61757`.

All QEMU integration used only a disposable regular-file-backed virtual disk, bounded scratch and timeout, and the current source hashes. The production SD/NFS diagnostic does not include this writer. H12 remains the single physical commissioning task; live eMMC CID matching, a production adapter, exact artifact and recovery review, and a separate high-consequence review still precede any hardware write.
