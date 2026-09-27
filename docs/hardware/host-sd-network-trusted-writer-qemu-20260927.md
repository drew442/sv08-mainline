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
| Abrupt guest loss after first flushed MiB | QEMU exited from `SIGKILL`; target prefix matched source, no success marker, consumed claim replay 409 | `56f057e4e080e79ee589dc7c928465cdfa91b91a7e78e982c73b5d1412cb8813` | `d67877e7f17c965c75cfdad8a6c16daf21e05504523e7da7eefa1857dea5b8de` |
| Injected flush fault | `INJECTED_AFTER_FLUSH`, target prefix matched source, no success marker, consumed claim replay 409 | `31b2915a7aad2012d56392576a62b6a42669205d1a4a80aa517e02187190864e` | `a92e0104d6c29c00b776abbd37e857379001f0b606a67d8f68414563e26c84ef` |
| Injected readback fault | `INJECTED_DURING_READBACK`, target prefix matched source, no success marker, consumed claim replay 409 | `21234e97b49d70f3a253037f0d69dfe8a0b3a7ac0a43bdfad4b0025ccf866d19` | `00e51ecfc5bc6b5ac2a3ea6dba2d3951a001f43412198631d7b13aa4b1eb1039` |

The checked-in `tests/host_qemu_sd_network_second_boot.py` reused each saved
case's **same** initramfs, NFS image, disposable target and consumed claim.
It started a fresh QEMU guest with the SD path still selected. For the old
success case, the real wall clock had passed the signed job's validity window;
that first replay safely emitted `REFUSED_STALE_JOB` before source hash or
target open. To isolate claim consumption from expiry, the harness sets QEMU's
synthetic RTC to ten minutes after the job's issue time. The second boots after
success, wrong-CID refusal and abrupt interruption then all emitted
`REFUSED_OR_UNCERTAIN_CLAIM`, did not hash the source or open the target, and
left the saved claim and target prefix unchanged.

| Second boot after | Result JSON SHA-256 | Guest serial SHA-256 |
| --- | --- | --- |
| Full success, synthetic clock in validity window | `ac3e3abebdddb77c2b2dad4cf2666074a966e5e3f6ccf1111813d40e18804ae2` | `a1c319ab1e8f684beec9f9e208fb22907eade290a4e2e925ada3a2d2617c2980` |
| Wrong-CID terminal refusal | `b74aaa58f797a72ab91af13d61f43059bed3dbb32f1fe8387c62449c1f7bb225` | `144a66410ea2c0d399327ab6ca70aa3ad527936b301044d0e595ab02a3afc99b` |
| Abrupt interruption | `ef8cd7fdc29e3a0fbeade53e38cfb29237d13ceea26317d6f7122f0213fbb895` | `f64bf6a449cf8557ced124f7aaaf206211e4eaa49228948c20ae42669404ec3c` |

An unconsumed claim is different: the forged-HTTP-200 case left its state armed.
If the operator leaves the explicit one-shot service running and manually
boots the same card again before job expiry, a genuine second claim could be
accepted. Stop the service after any terminal refusal; the controller never
restarts a stopped service or rearms a started job. There is no unattended
entry/return path or proof of physical next-boot behavior yet.

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

The final focused/regression offline Python run passed 47 tests covering the
H616 builder, signed job controller, real loopback claim, NFS export syntax,
trusted initramfs composition and existing SD writer behavior. No printer was
contacted during these checks.
