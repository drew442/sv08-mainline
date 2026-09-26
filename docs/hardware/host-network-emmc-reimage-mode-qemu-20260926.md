# Isolated QEMU reimage mode

Status: implementation and three disposable QEMU integration cases passed;
independent delivery review pending. Date: 2026-09-26. Scope: disposable QEMU
`virt` only. This is **not a deployable printer image**.

The default [SD/NFS diagnostic builder](../../scripts/build_sd_network_image.py)
still compiles only the read-only probe init. Its U-Boot script selects a
read-only NFS root, and its root manifest has one executable,
`sd-network-init`. It has no reimage writer, job, claim trigger or writable
service. The separately selected
[`qemu-reimage` builder](../../scripts/build_qemu_reimage_mode.py) emits an NFS
root bundle and manifest, deliberately no SD boot image or H616 loader. The
bundle holds the same [writer](../../tests/fixtures/sd-network-root/emmc_image_writer.c)
used by the [QEMU harness](../../tests/host_qemu_sd_network_emmc_write.py).
The writer requires QEMU `virt` device-tree compatibility, read-only NFS root,
the explicit QEMU command-line mode, a test-only USB serial/capacity, synthetic
MMC CID/type/size/dev_t, and a matching opened target descriptor. It has no
physical H616 target adapter. Even if this bundle is copied to an H616 root,
its virtual-machine guard refuses it before the target open.

The job is canonical UTF-8 JSON with a trailing newline and exact fields:
`format`, `job_id`, `issued_unix`, `expires_unix`, `source`,
`target_policy_sha256`, and `image`. The source binds its byte count,
SHA-256 and read-only NFS mode. The image binds the same 7,818,182,656-byte
extent/hash and the exact six-partition GPT map, including disk GUID and backup
GPT at image end. The separate, local synthetic policy binds CID
`00000000000000000000000000000001`, 61,079,552 MMC sectors, `8:0`, QEMU
USB serial, 32,000,000,000-byte disposable target capacity and image extent.
The policy is never selected by job data. The test-only detached Ed25519
signature covers all canonical job bytes. The committed
[test verification key](../../tests/fixtures/sd-network-root/synthetic-keys/test-verification-key.pem)
is the trust anchor; the [synthetic private key](../../tests/fixtures/sd-network-root/synthetic-keys/test-signing-key.pem)
is public test material and gives **no production authenticity**. The builder
rejects missing/altered/wrong-key/noncanonical/stale jobs and wrong layout or
policy before constructing the root. It compiles the verified job digest,
source hash, validity window, signature digest and policy digest into the
writer. The guest checks those pinned bytes before the durable one-shot claim
and target open. It does not perform a second Ed25519 operation: signature
verification is the builder's admission gate, and the trusted writer binary
binds the resulting exact job and signature. A native test changes each of the
three bundle files after construction and confirms guest admission refuses.

The claim service persists a claim keyed by the verified job digest before
the first target open. The writer holds the opened source and target descriptors
through writing and readback; it rechecks CID-to-dev_t immediately before the
first write. A changed source, identity drift, interrupted transfer, failed
flush or readback produces no success and cannot rearm the claim. The claim
HTTP transport and the replaceable SD/NFS boot media are test fixtures; this
signature authenticates job bytes during bundle construction, not the boot
chain or a future production trigger. Physical adapter, key provisioning,
current live CID mapping, fault recovery and release qualification require
separate review under [H12](coordinated-human-tasks.md).

Focused offline checks from this worktree:

```text
python3 -m unittest tests.test_qemu_reimage_mode tests.test_sd_network_emmc_write tests.test_sd_network_image -q
23 tests passed (14.76 s)
aarch64-linux-gnu-gcc -static -Os -D_FORTIFY_SOURCE=2 -Wall -Wextra -Werror ... emmc_image_writer.c
passed
git diff --check
passed
```

The builder reproducibility test makes two independent roots from the same
signed job and compares their full manifest and writer bytes. Full QEMU
transfer, readback and failure tests ran on Beelink 2026-09-26 from source
commit `7e2dee5f336cead95a7be951b4dfc8dee5a46167` (tree
`c596c2032e2688b70e77a95cd32a0c76246ad059`, matching staged file digest
`81d5095be576e853770991ca8c971fe88b57e82ec97dd987ed2ca79095c12b4a`). The
work used a private network/mount namespace, bounded `timeout -k 10 4700`,
2 GiB ARM64 QEMU guest and disposable regular-file-backed target. Beelink had
10,758,328,320 bytes free and 7,398,158,336 bytes `MemAvailable` at preflight;
after cleanup it had 10,749,894,656 bytes free. The development VM was not used
for raw image or target storage.

| Case | Result | Elapsed / max RSS | Claim and target | Receipt SHA-256 | Serial SHA-256 |
| --- | --- | --- | --- | --- | --- |
| Full signed-job transfer | Passed: source, guest readback and independent host readback all matched 7,818,182,656 bytes at SHA-256 `7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`; primary and backup GPT CRCs, disk GUID and all six partition records matched. | 43:51.62 / 2,311,484 KiB | Claim consumed before write; 32,000,000,000-byte QEMU target; source extent remained 7,818,182,656 bytes. | `23b42f83656fdaf2c88de58ca297d2fb032b5e88ce12af25cabfe44893d76d58` | `4d5c4ee4374e3ea7210135102fb0ab7865d528b6473812b76828d15086756824` |
| Wrong CID | Passed refusal at `SV08_QEMU_REIMAGE_REFUSED_SYNTHETIC_MMC`; claim consumed, replay HTTP 409, target unchanged, no success receipt. | 1:26.33 / 387,828 KiB | Separate disposable target. | `63bfe3690539d453c86e8c134448ebb9f5ea9531135706f7aa0962e6c86a3359` | `0d3cdf0f9822781926619cf8d7f24ab4fc04819a92ed68c3e5544bce31bd7635` |
| Partial write | Passed terminal stop at `SV08_QEMU_REIMAGE_INJECTED_PARTIAL_WRITE`; first 1 MiB matched the source, claim consumed, replay HTTP 409, no success receipt or retry. | 17:14.76 / 2,306,260 KiB | Separate disposable target. | `6680de6814e18379bc32e6e5c69ac8e414b4f1753a553cb0165ebbe26b346fef` | `3f24aa8557ae85a66fb08dd1bee64e082f25ce6965b7210cac66fa9c64fd3870` |

The full guest emitted two `GFP_ATOMIC` allocation warnings, but no OOM kill or
NFS failure; transfer, guest readback and independent host validation passed.
Peak guest-host RSS values come from `/usr/bin/time -v`; exact raw result JSON,
serial logs and timing records are retained privately under
`local/integration-evidence/network-emmc-reimage-mode/{full,wrong-cid,partial-write}`.
The public receipt hashes above were checked against those private files.

This is still only QEMU synthetic evidence. In particular, it does not show
that the H616 kernel maps the live eMMC CID to the expected opened descriptor,
does not test physical eMMC power-loss or recovery behavior, and does not
authorize an eMMC or boot-policy write. H12 still requires live CID comparison,
exact image/target/recovery review, independent high-consequence review and
explicit action authorization before a physical test.
