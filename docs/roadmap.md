# Roadmap

## 0. Foundation — initial intake complete

- Define the stock-first, modified-electronics-capable scope and agent workflow.
- Gather primary board/chip references with evidence levels.
- Initialize and pin five upstream reference/source submodules.
- Record a stock profile as research-only, with unknowns explicit.

This phase establishes inputs; it does not validate firmware or printer operation.

## 1. Identify and preserve the stock system — in progress

Prepared a read-only host collector with offline fixture tests and a
[discovery/backup workflow](hardware/discovery-and-backup.md). Physical inspection
and full backup/recovery evidence remain outstanding.

[Test printer 01](hardware/test-sv08-01.md) is identified by its owner as mostly
factory electronics with a 10 mm bed, upgraded hotend, enclosure and dual displays.
Its [first live inspection](hardware/test-sv08-01-discovery.md) identifies a
vendor-derived stack, two different MCU builds and mostly vendor thermal settings.
The initial hotend temperature anomaly is no longer observed after owner-reported
thermistor repair; a read-only recheck found stable ambient readings with unchanged
sensor settings. Heated-range validation remains outstanding. Raw captures remain private.

The approved private configuration archive parses to the same 116 sections as
the captured running configuration. Existing mainboard firmware files match the
pinned vendor artifacts; [file inspection](hardware/test-sv08-01-firmware.md)
identifies an 8 MHz/zero-offset build candidate, without establishing installed
flash contents. HDMI and USB touch paths are detected. The owner has an ST-Link,
eMMC USB reader and spare 32 GB module; the
[recovery plan](hardware/test-sv08-01-recovery.md) preserves the original module
as the owner-selected host rollback baseline and builds a fresh
[host bring-up image](hardware/test-sv08-01-image.md) for the blank spare.
A full factory image file is optional for this host-only experiment. Both eMMC boot
regions and the user-area prefix now have matching repeat-read captures, with
decoded eMMC metadata preserved privately. Full disk and MCU backups remain
outstanding. The [hands-on task list](hardware/test-sv08-01-recovery-tasks.md)
provides the spare write/boot steps and independent MCU preservation tasks.

Capture PCB revisions, processor markings, host OS/boot/device-tree information,
MCU identities, existing configs, and flash/clock settings. Obtain recoverable
host and MCU backups, recording hashes and a restore plan. Reconcile the published
schematics with the actual boards.

Exit evidence: a populated stock hardware record, private backup inventory,
reviewed recovery procedure, and resolved settings for each MCU build target.

## 2. Audit vendor behavior and select the stack

An [initial static compatibility audit](vendor-compatibility.md) records removed
configuration options, vendor extras, probe API differences, and missing includes.
The complete vendor delta and runtime behavior remain to be investigated.

Compare Sovol's Klipper changes, probing/Z-offset routines, macros, thermistor
handling, and optional services against current upstream. Create a feature matrix:
upstream equivalent, required configuration, custom implementation, or explicitly
deferred. Evaluate the OS/kernel/device tree and boot chain independently.

Exit evidence: architecture decisions, selected candidate revisions, compatibility
gaps with reproductions, and a minimal custom-code plan where needed.

## 3. Reproducible builds and offline validation — host candidate built offline

The first image assembles fresh Debian 13 arm64 from a dated snapshot with
captured vendor boot support; see [decision 0002](decisions/0002-first-emmc-image.md).
It stages the selected Klipper source but does not activate printer services or
include MCU firmware. This is not a source-reproduced boot chain or a supported
printer image. On 2026-09-06 the owner reported successful boot on the new
eMMC; detailed host validation and full stack builds remain outstanding. The
[image capture guide](hardware/imaging-emmc.md) now covers preserving the installed
module on Windows, Linux and macOS.

Record toolchains, build dependencies, per-MCU configs, patches, and artifact
hashes. Build the host integration and both MCU targets. Check configuration
compatibility and regression-test custom behavior. Keep flashing separate.

Exit evidence: repeatable build instructions and artifacts tied to a project
revision. Builds alone do not advance hardware support status.

## 4. Stock hardware bring-up and conversion guide

Validate boot/storage/network reliability and persistent MCU identity. Follow
Klipper's configuration checks for sensor readings, fans, endstops, and motion;
then validate probing, homing, gantry leveling, heaters, and mesh. Measure the
temperature path before accepting vendor thermistor settings. Exercise shutdown
behavior and recovery, and record limitations.

Exit evidence: named-board bench results, representative print results, tested
recovery, and a clean-system conversion reproduced from the documentation.

## 5. Modified profiles and maintenance

Add explicit profiles for replacement hosts, mainboards, toolheads, probes, and
transports. Reuse shared mechanics while validating each changed electrical
interface and firmware target. Automate candidate update checks and regression
builds; publish supported combinations only with the associated test records.

## Open decisions

- Exact installed board revisions, recovery adapter models and spare-module compatibility.
- OS/image builder, kernel line, bootloader, and device-tree strategy.
- Treatment of vendor probing and power-loss recovery features.
- First modified-electronics combination to support after stock.
- License for original code/documentation, before external contributions/releases.
