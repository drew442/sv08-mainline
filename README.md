# SV08 Mainline

A project to convert and run the Sovol SV08 on current, maintainable software
and firmware, with reproducible builds, documented recovery, and custom code
where upstream support is insufficient.

Stock electronics are the first target. Modified mainboards, Linux hosts,
toolheads, probes, and displays will be supported through explicit hardware
profiles. A profile being present does not mean it has been tested.

**Status: hardware research and first host-image candidate.** A private
[spare-eMMC host image](docs/hardware/test-sv08-01-image.md) has been built and checked offline
for test printer 01. It is not a printing system or validated hardware release;
the owner reported booting it on the spare eMMC on 2026-09-06. Printer
configuration, MCU firmware replacement and detailed hardware validation remain
outstanding. [Katapult and matching Klipper candidates](docs/hardware/test-sv08-01-mcu-build.md)
now build offline; [USB updates and paired MCU communication](docs/hardware/test-sv08-01-mainboard-usb.md)
are verified on test printer 01. Printing remains unvalidated.

## Start here

- [Project definition](docs/project.md): scope, architecture, and success criteria.
- [Hardware inventory](docs/hardware/stock-sv08.md): evidence and open questions.
- [Test printer 01](docs/hardware/test-sv08-01.md): reported upgrades and inspection scope.
- [Discovery and backup preparation](docs/hardware/discovery-and-backup.md): collect
  host evidence and define the preservation record.
- [Capture an eMMC image](docs/hardware/imaging-emmc.md): offline backups on
  Windows, Linux and macOS.
- [Reference library](docs/references.md): schematics, datasheets, and upstream docs.
- [Upstream sources](docs/upstreams.md): submodules, pins, and update workflow.
- [Vendor compatibility audit](docs/vendor-compatibility.md): known migration gaps.
- [Host OS and A/B design](docs/design/host-os-ab.md): OS/kernel assessment,
  update design and owner choices.
- [Full host stack build](docs/hardware/host-stack-build.md): pinned application packages and capacity validation.
- [Host state and update tests](docs/hardware/host-state-build.md): operating modes, persistence and signed A/B fixtures.
- [ARM64 RAUC validation](docs/hardware/host-rauc-build.md): reproducible package and inactive-partition installation.
- [Host administration and recovery UI](docs/hardware/host-admin-ui.md): browser/native interfaces and integration status.
- [Host completion checklist](docs/hardware/host-os-tasks.md): remaining offline and human tasks.
- [Host application packaging](docs/hardware/host-apps-build.md): Klipper `.deb` and offline checks.
- [Armbian source intake](docs/hardware/host-ab-armbian-intake.md): unverified SV08 boot-support candidate.
- [New host build work](docs/hardware/host-ab-build.md): offline Debian baseline,
  factory-capacity layout and driver audit.
- [Roadmap](docs/roadmap.md): the next work and its acceptance criteria.
- [Feature agent framework proposal](docs/design/feature-agent-framework.md):
  suggestion, improvement, approval and continued delivery; awaiting owner approval.
- [Contributing](CONTRIBUTING.md) and [agent instructions](AGENTS.md).

## Get the sources

From a checkout of this repository, with Git and network access:

```sh
git submodule update --init --depth 1
git submodule status
```

This initializes the seven direct submodules at their recorded commits. Nested
vendor dependencies are deliberately not initialized by this command; initialize
them individually if a specific build needs them. Downloading sources does not
install software or change a printer.

| Path | Purpose |
| --- | --- |
| `upstream/sovol-sv08/` | Sovol schematics, configuration, and vendor source snapshot |
| `upstream/katapult/` | USB MCU bootloader for host-driven updates |
| `upstream/klipper/` | Upstream Klipper host software, MCU firmware, and documentation |
| `upstream/sunxi-tools/` | Allwinner host diagnostics and FEL tooling |
| `upstream/moonraker/` | Klipper API service |
| `upstream/mainsail/` | Web interface |
| `upstream/klipperscreen/` | Required HDMI touchscreen UI |
| `profiles/` | Hardware identities and compatibility records |
| `docs/` | Design, evidence, decisions, and validation plans |

“Latest” means recent upstream revisions evaluated and pinned as a complete
stack. Initial pins are research candidates, not a supported release. Mainline
Klipper and mainline Linux are separate milestones.

Third-party material retains its own license. The license for original project
work remains to be selected; see [licensing](docs/licensing.md).
