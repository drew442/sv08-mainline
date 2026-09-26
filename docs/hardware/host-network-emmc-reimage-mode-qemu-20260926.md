# Isolated QEMU reimage mode

Status: implementation and focused checks complete; full QEMU integration and
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
transfer, readback, GPT checks, runtime and resource numbers must be added from
the assigned Beelink integration run before this feature can pass `nrm-03`.
The test must use a bounded disposable regular-file target and recheck free
space first; the development VM is too full for a whole-image run.
