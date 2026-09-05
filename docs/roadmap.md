# Roadmap

## 0. Foundation — initial intake complete

- Define the stock-first, modified-electronics-capable scope and agent workflow.
- Gather primary board/chip references with evidence levels.
- Initialize and pin five upstream reference/source submodules.
- Record a stock profile as research-only, with unknowns explicit.

This phase establishes inputs; it does not validate firmware or printer operation.

## 1. Identify and preserve the stock system — in progress

Prepared a read-only host collector with offline fixture tests and a
[discovery/backup workflow](hardware/discovery-and-backup.md). Printer access,
physical inspection, and actual backup/recovery evidence remain outstanding.

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

## 3. Reproducible builds and offline validation

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

- Exact installed stock board revisions and available recovery adapters.
- OS/image builder, kernel line, bootloader, and device-tree strategy.
- Treatment of vendor probing and power-loss recovery features.
- First modified-electronics combination to support after stock.
- License for original code/documentation, before external contributions/releases.
