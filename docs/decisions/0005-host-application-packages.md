# 0005: Image-owned application packages

Date: 2026-09-09. Status: implemented offline; activation and release validation pending.

The [host design](../design/host-os-ab.md) selects coordinated OS/application
updates and deb/apt ownership. Upstream source archives and web ZIP files do not
provide the project's pinned host/MCU and Python runtime composition. Build
project `.deb` payloads containing source plus isolated hash-locked venvs, or
Mainsail static assets. Use dpkg and supported upstream execution paths. Keep
service configuration, state migration, hardware writes and activation separate.

Klipper's revision continues to match both MCU targets. Moonraker/Mainsail pins
are unchanged. Add KlipperScreen as a direct pinned submodule for required HDMI
support. Use Debian PyGObject for its native GTK integration and a venv Pycairo
wheel matching the selected source requirements; record both dependency layers.
Build compiler-dependent wheels in a separate chroot, not on the printer.

Two demonstrated gaps justify small archive-only patches: KlipperScreen reads
packaged version metadata instead of requiring Git, and Mainsail's Workbox build
uses deterministic precache ordering without duplicate asset collection. Each
patch is hashed in its package profile, tested, documented with reproduction and
an upstreaming/retirement plan. No upstream checkout is modified. No upstream
messages are sent as part of implementation.

The custom wrappers are release-composition glue; retire them when maintained
upstream/distro packaging provides equivalent pinned payloads. The lock exporter
uses upstream's dependency graph rather than resolving new versions. It marks
missing ARM64 wheels for explicit source builds. Snapshot updates and dependency
updates are distinct reviewed source changes, not installer side effects.

A `.deb` installing successfully does not prove bootability, immutable-mode
operation, update atomicity, GUI hardware support or printing. Test each layer
separately and retain truthful status. First artifacts remain private build
outputs; documented dependency audit findings and unresolved licensing/release
review prevent describing them as a supported release. See the
[build record](../hardware/host-stack-build.md) and
[remaining gates](../hardware/host-os-tasks.md).
