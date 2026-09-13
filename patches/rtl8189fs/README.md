# RTL8189FS strict-compiler compatibility

2026-09-13. This patch applies to
[`EvilOlaf/rtl8189ES_linux`](https://github.com/EvilOlaf/rtl8189ES_linux/tree/be148d226d22214a173e5b2dfe4287e53685ceda),
commit `be148d226d22214a173e5b2dfe4287e53685ceda`. The retained source archive
SHA-256 is `c56e850ab1b1c11baa2489baa1a94ec40e70ee2bc31647061e8df8a94c67c67b`.
Sources inspected 2026-09-13. Keep the driver's existing GPL licensing.

The [patch](0001-strict-flex-arrays-and-thread-format.patch), SHA-256
`38ead4b3b1ff40c96ff9cff9c066718c8a432a3a107b1b40934966c15efe4ae2`,
replaces two final zero-length string members with standard flexible arrays.
Their existing allocators reserve zeroed `sizeof(struct) + nlen + 1` bytes.
It also removes an overlapping `snprintf` in normal SDIO transmit-thread startup,
preserving the intended constant prefix. Linux's `thread_enter` ignores this
formatted name; no task-name change or observed crash is claimed.

Apply to a fresh extracted archive, outside `upstream/`:

```sh
patch --batch --fuzz=0 -p1 -d "$RADIO_SOURCE" \
  < patches/rtl8189fs/0001-strict-flex-arrays-and-thread-format.patch
python3 tests/rtl8189fs_compat.py "$RADIO_SOURCE"
make -C "$RADIO_SOURCE" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  KSRC="$KERNEL_OUTPUT" -j4
```

Use the kernel configuration, compiler and fixed build environment in the
[kernel artifact record](../../docs/hardware/host-kernel-compile-20260913.json).
The complete fresh module build retains `-fstrict-flex-arrays=3`. Warnings dropped
from 568 to 553: all 14 string-overread warnings and the startup overlap warning
disappeared. The remaining nine overlap warnings are in manufacturing/private
ioctl functions; avoid those paths in normal interface/scan trials. Another 514
missing-prototype, 24 address and six empty-body warnings remain. This is a
bounded compatibility fix, not a comprehensive driver audit.

The source-derived host C test checks formatting, truncation, termination,
allocated trailing strings and size/offset continuity, with undefined-behavior
sanitization. Its original-format negative control fails compilation. Struct
dependency shims exercise representative dimensions; the complete ARM64 module
build checks actual header integration. Neither establishes radio operation.

Built module SHA-256:
`43d029192940053507bf483551b9069acd771d4e309bcea6b31a839bdd37f430`.
After `aarch64-linux-gnu-strip --strip-debug`, installed-payload SHA-256:
`2d2422f75da9e993dda61ad7540a219736e8847863b360806bfbd11330e43e7d`.
Name `8189fs`, dependency `cfg80211`, alias `sdio:c*v024CdF179*`, vermagic
`6.18.51-sv08-candidate1 SMP preempt mod_unload aarch64` are preserved.
The original first-trial module/archive hashes remain historical evidence.

Upstream-ready rationale: support current kernel strict flexible-array semantics
and eliminate overlapping source/destination formatting without changing the
allocation contract or disabling warnings. No upstream message has been sent.
Retire this patch when a deliberately pinned upstream revision includes equivalent
fixes and passes these checks plus the required hardware validation.
