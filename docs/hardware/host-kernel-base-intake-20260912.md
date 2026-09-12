# Stock SV08 kernel-base recipe intake — 2026-09-12

**The pinned Armbian checkout does not determine an exact Linux 6.18 patchlevel
or commit.** It supplies a moving stable-branch recipe and an exact configuration
seed. The exact kernel revision and final `.config` remain unknown.

Primary sources accessed **2026-09-12**, pinned to Armbian build
`a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015`. This extends the
[6.18 platform intake](host-sunxi-618-intake-20260912.md) and
[radio/kernel intake](host-radio-kernel-intake-20260912.md). No kernel archive,
build, source adoption or hardware operation occurred. The
[test printer's](test-sv08-01-online-20260912.md) PCB revision remains unknown.

## Default selection chain

This traces an explicit `BOARD=sovol-sv08 BRANCH=current` selection with no user
overrides; no such build invocation was executed in this intake.

1. `lib/functions/main/config-prepare.sh:95–142` loads the board configuration and
   initially sets `LINUXFAMILY` from `BOARDFAMILY`. The
   [stock board file](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/config/boards/sovol-sv08.csc)
   selects `sun50iw9`, targets `current,edge`, and names
   `sun50i-h616-sovol-sv08.dtb`. `KERNEL_TEST_TARGET=current` is a recipe variable,
   not proof of a test.
2. `config/sources/families/sun50iw9.conf` includes `sunxi64_common.inc`, which sets
   `ARCH=arm64`, `LINUXFAMILY=sunxi64`, current `KERNEL_MAJOR_MINOR=6.18` and
   `KERNELPATCHDIR=archive/sunxi-6.18`. The family specifies H616 TF-A separately;
   existing [boot-source findings](host-cb1-boot-compile.md) remain distinct.
3. `config/sources/common.conf:131–159` defaults `LINUXCONFIG` to
   **`linux-sunxi64-current`**, sets an unset kernel source from the selected
   mainline mirror and invokes the mainline version hooks.
4. The [mirror selection](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/lib/functions/configuration/main-config.sh)
   defaults to `https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git`;
   explicit mirror and user/hook settings can change it. The previously reviewed
   `mainline-kernel.conf.sh` defaults to **`branch:linux-6.18.y`** when no override
   exists. Neither supplies a fixed 6.18 patchlevel or commit.
5. `kernel-git.sh` passes those source/branch variables to `fetch_from_repo`.
   `kernel.sh:33–42` records `checked_out_revision` as `kernel_git_revision` only
   after fetching. No corresponding exact fetch result is in this reviewed
   intake. Looking up the branch now cannot recover an unknown earlier fetch.

The [combined source record](host-kernel-base-intake-20260912.json) binds the
exact paths above to URLs, revision, access date, SHA-256 and Git blob IDs.

## Configuration seed and remaining transformations

[The seed](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/config/kernel/linux-sunxi64-current.config)
is 69,341 bytes and says it was generated with 6.18. SHA-256:
`03a427fed857cc598ef95c5c8a2dccb43bb515d513df1eff9c010e6aa56ab155`;
Git blob `55073a1b9915bc599d2411f0433723ea907d91d4`.

It explicitly enables AC300 PHY, sun4i DRM, sunxi MMC and AXP20X regulator/MFD
support, with RTL8189FS/ES as modules. This defconfig does not enumerate all
effective defaults; absent entries do not necessarily mean disabled features.
The new DE33 planes option, for example, derives its default in the patched tree.

`kernel-config.sh` permits userpatch or retained-config overrides, invokes
Armbian/custom configuration hooks and runs `olddefconfig`. `armbian-kernel.sh`
contains further core modifications. Therefore the seed hash is **not** a final
configuration hash. Exact kernel/Kconfig, patches, hooks and toolchain inputs
must be known before the effective configuration can be reproduced.

## Include and patch boundaries

The stock DTS is copied from the 6.18 archive and directly includes
`sun50i-h616-bigtreetech-cb1.dtsi`; the CB1 board patch modifies that existing
base-kernel file and supplies required labels and HDMI enablement. The display
`0041` patch modifies `sun50i-h616.dtsi`, adding DE2/TCON TOP clock and DE2 reset
headers. The previously reviewed DE33 binding/driver changes and CB1 AC300
inheritance remain part of the dependency review. Max and Zero are separate.

Complete transitive CB1/SoC/header contents **at the selected Linux SHA** remain
unresolved. Patch context is not a complete base file; an arbitrary tag's include
files cannot substitute for a missing selected revision. Preserve the final
preprocessed DTS and schema/DTB evidence after selecting and applying exact inputs.

`series.conf` is a declared sequence, not the entire effective build input.
`kernel-patching.sh` passes userpatch/filter inputs and generated driver patches
before the series. `drivers-harness.sh` can disable extras via `EXTRAWIFI=no`;
otherwise it contains multiple external-driver calls. Extra-source and config
hooks also matter. Neither the archive count nor one radio pin identifies the
complete applied tree.

## Provenance and blocker

Fourteen new small files (209,045 bytes) were downloaded; all SHA-256/Git blob
values were recomputed and matched the complete pinned tree. The paired JSON also
explicitly records **11 reused sources**, their hashes and the hashes of their
previously published intake records. Raw files remain in ignored local storage;
public links refer to published records or pinned primary sources.

To clear the blocker, recover an existing candidate's recorded full Linux SHA
and source URL, or select a new immutable base through the existing
[platform-adoption review](host-ab-armbian-intake.md#next-review-before-adoption).
Record effective overrides, ordered patches/copies/driver sources, include
closure, seed and final configuration, toolchain, firmware/licenses and resulting
artifact hashes. This intake makes no base selection and no compatibility claim.
The [physical acceptance checklist](host-os-tasks.md) remains authoritative.
