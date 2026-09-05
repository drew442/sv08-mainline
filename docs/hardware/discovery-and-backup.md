# Stock hardware discovery and preservation

Status: preparation, not a demonstrated recovery procedure. The collector has
offline fixture coverage and has run on [test printer 01](test-sv08-01-discovery.md).
That host inspection does not validate stock configuration or recovery.

## Collect host evidence

Run [`scripts/collect_hardware.py`](../../scripts/collect_hardware.py) on the
printer's Linux host with Python 3.7 or later. It uses the standard library and
does not need root. `lsblk` and `lsusb` are optional; unavailable commands, missing
files, read errors, and oversized files are reported explicitly.

For SSH access, from this repository on your workstation, replace `USER@HOST`
with the identified printer's SSH destination:

```sh
mkdir -p local/discovery
umask 077
ssh USER@HOST python3 - < scripts/collect_hardware.py > local/discovery/host.json
python3 -m json.tool local/discovery/host.json > /dev/null
```

Use a new output filename for each capture; shell redirection overwrites existing
files. Check the SSH command succeeded before accepting the JSON. The script is
sent over stdin and writes its report to the workstation, without installing
anything on the printer. Ordinary SSH/service logging may still record access.

Alternatively copy the script onto the printer and run:

```sh
umask 077
python3 collect_hardware.py > host.json
```

Move that report into private workstation storage. Do not commit raw reports:
USB identifiers, filesystem mount paths, and boot settings can identify a machine.
The collector avoids network credentials, printer configuration, and full boot
command lines; it is not a general-purpose redactor.

The report contains OS/kernel, memory, device-tree model/compatible strings,
selected boot-environment variables, storage topology, and USB/serial link
identities. It reads serial symlink metadata only, never opens MCU ports, and
does not issue G-code, stop services, or read/write raw block devices. Its file
hashes describe collected evidence, not a firmware or disk backup.

## Complete the physical inventory

Record mainboard/toolhead PCB revisions and chip markings, host SoC and storage
markings, and connector orientation against the published drawings. Record the
printer's existing firmware version and any modifications. Do not infer the
mainboard/toolhead mapping from `/dev/ttyACM0` versus `/dev/ttyACM1` alone.

Resolve each MCU's external clock, flash capacity, bootloader/application offset,
and recovery interface independently. Existing build files and Klipper logs are
supporting evidence, not proof that a file matches the running firmware. Collect
them privately when available, then publish only the relevant reviewed fields.

## Preserve before conversion

Create a private backup inventory with one record per artifact:

| Field | Required content |
| --- | --- |
| Identity | Printer/board identifier, revision, and capture date |
| Scope | Config archive, host storage region, mainboard flash, or toolhead flash |
| Capture | Tool/version, exact source device or address range, procedure |
| Integrity | File size and SHA-256 hash; readback/comparison results where available |
| Completeness | Regions included/excluded, required external config includes, consistency limits |
| Recovery | Matching restore method, tool/adapter, target identity checks, evidence of restoration |

Preserve printer configuration including external includes, calibration, macros,
service configuration, and any needed application state. Keep secrets private.
For a coherent full host backup, identify eMMC/SD and its relevant regions first;
prefer an offline capture or a documented consistent snapshot. A live file copy
does not establish a recoverable disk image. Record boot partitions separately
where relevant, rather than assuming a user-area image includes them.

For each MCU, choose a verified readout method after checking markings, wiring,
voltage, and protection state. Some operations that disable readout protection
erase flash; do not treat unlocking as a backup step. Stop if a read requires
an erase. ST documents that behavior for the STM32F10xxx in
[PM0075 Rev 2, sections 2.3.5 and 2.4.1, pages 17–18](https://www.st.com/resource/en/programming_manual/cd00283419-stm32f10xxx-flash-memory-microcontrollers-stmicroelectronics.pdf)
(checked 2026-09-05). Preserve the original flash regions needed for restoration and record
addresses and sizes, not just filenames.

The test-printer [hands-on task list](test-sv08-01-recovery-tasks.md) now includes
a conditional Linux raw disk read template. MCU commands and restore writes
remain deferred until target identity, flash layout and adapter compatibility
are verified. Test
printer 01 now has owner-reported adapters and a spare module; its
[recovery preparation plan](test-sv08-01-recovery.md) records the next checks.
Document the concrete commands once those inputs are established. Store
artifacts in ignored `backups/` and at least one separate private location;
verify hashes after transfer. Mark recovery verified only after demonstrating
restoration on the identified hardware.

## Accept evidence

Review the report and physical findings against
[`stock-sv08.md`](stock-sv08.md). Record discrepancies and retain unknown values
in [`profile.json`](../../profiles/stock-sv08/profile.json). Add a dated,
sanitized validation record before promoting any claim to verified-on-hardware.

Offline checks for changes to the collector:

```sh
python3 -m unittest discover -s tests -v
```
