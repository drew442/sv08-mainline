# 0007: Pinned RAUC package candidate

Date: 2026-09-10. Status: offline build and integration candidate.

## Decision and evidence

Build unmodified upstream RAUC 1.15.2 as a Debian ARM64 package for evaluation.
The [source/package record](../../configs/host-os/rauc-package.json) pins its commit,
archive hash, source date and build dependencies. Keep the distro-maintained
kernel choice. This does not adopt a new board bootloader or activate updates.

The initial native RAUC 1.13 install test failed before slot writes because it
rejected the workstation Linux 7.0 dm-verity status `V -`. RAUC 1.15.2's upstream
parser handles that format, and native signed/paired installation and rejection
tests pass. This finding is scoped to that workstation; it does not establish
that Debian's patched ARM64 1.13 package fails on the selected 6.12 kernel.
See the [integration evidence](../hardware/host-state-build.md).

Use the upstream Meson/Ninja build, explicit Debian installation paths,
`SOURCE_DATE_EPOCH`, compiler path remapping and `dpkg-shlibdeps` to create the
package. Build tools stay in a separate compiler root. The project script verifies
the supplied source archive before extraction and defaults to inspection. Package
creation, isolated installation and runtime validation remain separate operations.
The package contains upstream licensing text and source provenance; no private
signing key, system-specific RAUC configuration or service-enabling maintainer
script is included. Ordinary Debian package ownership and dependency resolution
apply; it replaces the package named `rauc` in the candidate image.

## Maintenance and retirement

This package introduces a project maintenance responsibility. Retire it when the
selected Debian release/backport supplies an acceptable version or fix and passes
the same signature, paired-slot, kernel and failure tests. A newer version alone
is not validated compatibility. Keep artifact and source manifests with releases,
and complete license/source distribution review before publishing binaries.

The [A/B state decision](0006-host-state-integration.md) still governs activation,
health confirmation, customization blocking and printer admission. A working
RAUC executable does not complete those integrations or validate the printer.
