# Trusted-initramfs reimage QEMU evidence, 2026-09-27

This is **offline synthetic evidence**, not a printer eMMC write. Beelink ran
`qemu-system-aarch64` in separate network and mount namespaces. Each guest
received only a fresh 31,272,730,624-byte regular file as a USB storage
target, a synthetic H616 identity fixture in the composed initramfs, and an
NFS export containing `image.bin` alone. The source was the deterministic
7,818,182,656-byte synthetic GPT image, SHA-256
`7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`.
The base SD kernel hash was
`5bc7c62df2b521610d0dea0a82b38aceb54af7d340a44b02a27428d6ea28dc34`;
the base diagnostic initramfs hash was
`8be88ee081ad61c64de216425b0318dd10f130f21dab54b20c60650f7d7438b2149b`.
For final-harness cases, the separate SD DTB supplied to compose the
hash-checked boot command was
`571288762747007542bb00c7ce04c2e0994678422e441975d928022588da9d3f`.
The first full-transfer case predated the boot-command hash tightening; it
used the same trusted initramfs and kernel arguments but no generated
`boot.cmd`. Later refusal cases used the final harness and generated a command
containing exact hashes of their composed kernel, initramfs and DTB.
Independent archive inspection found `trusted-writer`, `job.json`, `job.sig`,
the target policy and the synthetic MMC fixture in the composed initramfs.
The NFS export held only `image.bin`. The unchanged diagnostic initramfs had
no `trusted-writer` entry.

The successful full-transfer case emitted `SOURCE_HASH_START`,
`TARGET_OPEN_START`, `SOURCE`, `READBACK` and `PASS`. Both source and guest
readback hashes matched the pin. After the guest powered off, the host harness
independently hashed the first 7,818,182,656 bytes of the disposable target,
matched the source, and verified the primary and backup GPT CRCs and all six
partition records. The claim was consumed durably before the target open.
The guest kernel logged two atomic page-allocation warnings during transfer;
I/O continued and the independent readback passed. These warnings still limit
performance and stability conclusions.

| Case | Observed result | Result JSON SHA-256 | Guest serial SHA-256 |
| --- | --- | --- | --- |
| Full transfer | `qemu-only-pass`; guest and host readback matched | `f84daf6b07c82462434ba8294d69bf70b1cbc317614451c7d7dd0c701cfd7e2f` | `c892660304414cf6bf85b71f01b8355bfc3f8de81cbeb868f338cee6aff7b7a5` |
| Wrong CID | `REFUSED_TARGET_ID`, no source hash or target open; consumed claim replay 409 | `9dee8e904f4306af3b275bf9266dfabe6f50bb5f40fe106993f4e2c4fd7a89f1` | `f74018b438faeb88d5205c2690b92f5a7716a4f333edb652e9ed5c12d8ec90cc` |
| Lost claim acknowledgement | `REFUSED_OR_UNCERTAIN_CLAIM`, target unchanged; replay 409 | `c02831bb3fbb035867275621ff7b12082c713520b3d457b54c3a4fc64c35cdad` | `98cdff3dee9e794b0df979b059f5043ef1f1ba5d1ef2198500add7cde97f1de8` |
| Wrong source size | `REFUSED_SOURCE`, no source hash or target open; target unchanged | `e4c157ca74799948da4055eab766b48655116163bd060e6da28d601e39fb6df4` | `ba93480b3f7badce9239126aba6fa647ebe162ec0e10ee9f9c3eb4e680f77910` |
| Wrong source hash | `REFUSED_SOURCE_HASH` after full source read, no target open; target unchanged, replay 409 | `4b4711d1af29e37c5222027070d541e96c94b7fa3ecc1bf80864e765ef2d2b02` | `01e73244d79e6d9f24b2bf8cf873fb1838e03a407cb1b7a5cfde6506c921fa2c` |
| Forged HTTP 200 | `REFUSED_OR_UNCERTAIN_CLAIM`, claim stayed armed; target unchanged | `bb0adbdba85eb98912e94b841980b99819e3d7bd4462aefb3bcc370df1a2bbbd` | `09884e75193319de6db1ff383b787fed160ec2988fc4bb408342a5ef4f7020bf` |

The full-transfer composed initramfs SHA-256 was
`31982b6764cb477d9ec9b90580507773be226b491a9250467f4ad5a38cd828c6`.
Beelink used a dedicated 24 GB ext4 scratch LV so the VM root filesystem did
not have to hold two raw image copies. The observed scratch use after the first
five cases was under 1 GB because the synthetic image and target are sparse;
the capacity requirement remains higher for nonsparse inputs.

The generated NFS-Ganesha config also reached `NFS SERVER INITIALIZED` using
the extracted Ganesha 4.3 package in a disposable Beelink network/mount
namespace. The smoke test assigned `192.0.2.10` to its private loopback,
started `rpcbind`, and opened the configured NFS listener. It inserted the
extracted package's plugin directory, which an installed system package would
normally discover itself. This checks parsing and startup, not the one-client
read-only ACL or a physical printer NFS mount. It caught and corrected two
config issues before delivery: Ganesha requires an unquoted IP token for
`Bind_Addr`, and the extracted package needed an explicit idmap file even
with NFSv3 selected.
The reproducible harness is `tests/host_ganesha_config_smoke.py`, run under
`sudo unshare -n -m --` with a fresh `--work` directory and the extracted
`--package-root`. Its final config SHA-256 was
`88496641713a30f9fd4ac4cb424ca17c29ebbebf6cb1b5879939c83392aba2e2`,
and result JSON SHA-256 was
`0d0604552b17293f26c310a09f008b3b0c340bbacf7aaa8449e603ed730ac201`.

The default SD diagnostic remains writer-free. These tests cannot establish
SoC secure boot, a live CID or dev_t match, actual eMMC behavior, power-loss
recovery, automatic return to eMMC boot, or release suitability. The SD card
is not SoC-authenticated; custody of the card remains part of the commissioning
assumption. H12 remains the only physical-write gate, including fresh live
identity and artifact review and an immediate independent high-consequence
review.
