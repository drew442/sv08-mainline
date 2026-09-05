# SV08 Mainline

A project to convert and run the Sovol SV08 on current, maintainable software
and firmware, with reproducible builds, documented recovery, and custom code
where upstream support is insufficient.

Stock electronics are the first target. Modified mainboards, Linux hosts,
toolheads, probes, and displays will be supported through explicit hardware
profiles. A profile being present does not mean it has been tested.

**Status: project foundation and hardware research.** No installable image,
validated printer configuration, or tested flashing procedure exists yet.

## Start here

- [Project definition](docs/project.md): scope, architecture, and success criteria.
- [Hardware inventory](docs/hardware/stock-sv08.md): evidence and open questions.
- [Test printer 01](docs/hardware/test-sv08-01.md): reported upgrades and inspection scope.
- [Discovery and backup preparation](docs/hardware/discovery-and-backup.md): collect
  host evidence and define the preservation record.
- [Reference library](docs/references.md): schematics, datasheets, and upstream docs.
- [Upstream sources](docs/upstreams.md): submodules, pins, and update workflow.
- [Vendor compatibility audit](docs/vendor-compatibility.md): known migration gaps.
- [Roadmap](docs/roadmap.md): the next work and its acceptance criteria.
- [Contributing](CONTRIBUTING.md) and [agent instructions](AGENTS.md).

## Get the sources

From a checkout of this repository, with Git and network access:

```sh
git submodule update --init --depth 1
git submodule status
```

This initializes the five direct submodules at their recorded commits. Nested
vendor dependencies are deliberately not initialized by this command; initialize
them individually if a specific build needs them. Downloading sources does not
install software or change a printer.

| Path | Purpose |
| --- | --- |
| `upstream/sovol-sv08/` | Sovol schematics, configuration, and vendor source snapshot |
| `upstream/klipper/` | Upstream Klipper host software, MCU firmware, and documentation |
| `upstream/sunxi-tools/` | Allwinner host diagnostics and FEL tooling |
| `upstream/moonraker/` | Klipper API service |
| `upstream/mainsail/` | Web interface |
| `profiles/` | Hardware identities and compatibility records |
| `docs/` | Design, evidence, decisions, and validation plans |

“Latest” means recent upstream revisions evaluated and pinned as a complete
stack. Initial pins are research candidates, not a supported release. Mainline
Klipper and mainline Linux are separate milestones.

Third-party material retains its own license. The license for original project
work remains to be selected; see [licensing](docs/licensing.md).
