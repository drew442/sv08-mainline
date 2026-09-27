# Authenticated one-shot eMMC claim: offline evidence

Date: 2026-09-27. Status: implementation and synthetic QEMU evidence complete;
independent delivery review pending. No printer was accessed and no physical
storage was opened or written.

The guest previously trusted an unauthenticated HTTP 200/body as proof that the
one-shot claim had been consumed. The new protocol uses a fresh 32-byte
`getrandom()` challenge and a canonical versioned receipt binding the exact job
ID, descriptor SHA-256 and current challenge. The guest accepts only exact HTTP
framing and a valid Ed25519 signature before it proceeds to source hashing or
target open. The claim service signs only after its state file and containing
directory are durably synced. Lost acknowledgements and ambiguous persistence
remain consumed and cannot automatically retry or rearm.

Ed25519 uses pinned Monocypher 4.0.3, commit
`ab2b16dd619ad5f6979a4fbe69cfa324a6fcc35f`, with the BSD-2-Clause option
selected from the upstream BSD-2-Clause OR CC0 license. ARM64 static compilation
uses Ubuntu GCC 13.3.0, `-Os`, `_FORTIFY_SOURCE=2`, warnings as errors, and
section garbage collection. The linked writer binary is 777,864 bytes
(SHA-256 `1ae050e92af87bde7d1e53665d5e24d451f1f823ba15bbea0d477463ce4db9c9`);
the writer source SHA-256 is
`0e8c917b9bc6eacf4fc865b41d3a1889a554c383e8f85d63f111e9c54110cf8b`. The
reimage manifest SHA-256 is
`a2d00bf0699c79fd874f4e4a5b72dfa3a78102a28ccfcc93f828b79c49ab5bfc`.
The manifest records all dependency source hashes, the separate test verifier
hash, and `bootable_sd_image: false`,
`claim_trigger_provisioned: false`, `physical_target_validated: false`, and
`status: nondeployable-commissioning-candidate`. The signing key is a synthetic
test fixture only; no production signer was provisioned.

The focused local checks passed:

```text
python3 -m py_compile <changed Python build, server, harness, and test files>
python3 -m unittest tests.test_h616_reimage_candidate tests.test_qemu_reimage_mode \
  tests.test_sd_network_emmc_write tests.test_sd_network_cid_admission \
  tests.test_sd_network_image tests.test_emmc_job -q
56 tests passed (31.3 s)
```

Beelink ran each guest in a private network/mount namespace against disposable
sparse regular-file targets; the 7,818,182,656-byte synthetic source and target
files stayed on Beelink. No source image was copied to the development VM.

| Case | Result | Evidence |
| --- | --- | --- |
| Valid claim only | Signature accepted; challenge consumed; target never opened. Guest max RSS 596 KiB. | `result.json` SHA-256 `f373b1867bfac4c468d1fe2b649dfe0fee52cf5166a7fff2528a9cad3ca7262d`; serial SHA-256 `d407b6fbc6687ef4759674b918461409b9918f7f13f4a8c7d5f8a5c565d9dbed`. |
| Full transfer | 7,818,182,656 bytes written and read back; host/guest/source hashes match `7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`; both GPT CRCs and all six partition records match. Guest max RSS 452 KiB. | `result.json` SHA-256 `4f75f151408c4850070ad657bfb29db42d0970e40c3226db056be87c0307ff2f`; serial SHA-256 `9e5307ccc36c5f37b8cb0129d6a70e64d8b7a8907c41ca043f34842c756b424b`. |
| Forged unsigned HTTP 200 | Refused before source hashing and target open; target unchanged; real one-shot still armed and unconsumed. This is the corrected final-harness rerun. | `result.json` SHA-256 `cde31d91faafcc59cdcdc784e9e9c5732e2ecd2ffc81fa4eddbfb58d1fdd72b0`; serial SHA-256 `98d8548c4bfe69c851d0c20eeadae991096d0b5f1e8eb252bc26d6fbf359f25d`. |
| Lost claim acknowledgement | Durable claim consumed, acknowledgement lost; guest refused before source hashing/target open; replay returned 409 and target stayed unchanged. | `result.json` SHA-256 `96209605309e36479fed1af5cfe5b58092f2c7b84918120dc2da2bba9346bf8e`; serial SHA-256 `f68dd6729a6d02f5efa3f979d432d0d5d63f381bc3a328adaf096aaa284032ba`. |
| Abrupt after first MiB | Full source hash completed, target opened and first MiB written/fsynced; host killed only QEMU. Prefix matched source, claim remained consumed, replay returned 409, and no success receipt was emitted. This models abrupt guest-process/VM interruption, not physical power loss. | `result.json` SHA-256 `57465ddf55d5108c1ee57028398b1455236b5c1ccd6d8f18f14fd90e3950aaae`; serial SHA-256 `8eecd9f2b27be219072e525e8fd222369f56847104a0577f47909602bcdb021d`. |

Native tests also cover invalid random-source behavior, wrong key/job/descriptor,
stale and altered challenge receipts, malformed or extended response framing,
interruption around durable publication, signer failure after consumption, and
replay. The earlier unauthenticated forged-ack run was discarded because the
harness reported target/claim status incorrectly; only the corrected final case
above is evidence.

These results establish only the bounded offline protocol and synthetic H616
writer path. They do not test the H616 Boot ROM/SPL/U-Boot chain, physical MMC
CID-to-`dev_t` binding, a real printer write, power-loss recovery, production
signer provisioning, or bootable SD construction. A network attacker can still
cause denial of service by consuming the one-shot claim first, but cannot forge
an accepted receipt. The board candidate remains nonbootable and
nondeployable; H12 and a separate exact-target high-consequence review remain
required before any physical write.
