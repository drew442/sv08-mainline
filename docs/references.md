# Reference library

Started and checked: 2026-09-05. This is a curated index, not a compatibility
endorsement. Vendor board files are available offline in the pinned Sovol
submodule. Other documents are linked at their publisher; download/version and
checksum the exact document when a build or hardware decision depends on it.

## Board documents and stock behavior

| Reference | Use |
| --- | --- |
| [Sovol SV08 source](https://github.com/Sovol3d/SV08) | Manufacturer's hardware and software snapshot; local `upstream/sovol-sv08` |
| [Mainboard MCU schematic](https://github.com/Sovol3d/SV08/blob/main/Motherboard/H616_JC_6Z_V1_2_MCU.pdf) | STM32F103VET6 and MCU signal connections |
| [Toolhead MCU schematic](https://github.com/Sovol3d/SV08/blob/main/Motherboard/Extra_MCU.pdf) | STM32F103CBT6 and toolhead signals |
| [Mainboard connector drawing](https://github.com/Sovol3d/SV08/blob/main/Motherboard/MCU_PIN_definition.pdf) | Physical connectors; check PCB revision and orientation |
| [Toolhead connector drawing](https://github.com/Sovol3d/SV08/blob/main/Motherboard/Extra_PIN_definition.pdf) | Toolhead connectors |
| [Stock printer configuration](../upstream/sovol-sv08/home/sovol/printer_data/config/printer.cfg) | Vendor configuration snapshot; behavior requires audit |
| [Sovol SV08 wiki](https://wiki.sovol3d.com/en/SV08) | Manufacturer manuals and troubleshooting index |

Local [printer configuration](../upstream/sovol-sv08/home/sovol/printer_data/config/printer.cfg)
and [vendor probing implementation](../upstream/sovol-sv08/home/sovol/klipper/klippy/extras/probe_pressure.py)
are pinned by the parent gitlink; web `main` links can change.

## Processor and peripheral documentation

| Reference | Use and provenance |
| --- | --- |
| [H616 documentation and support status](https://linux-sunxi.org/H616) | Maintainer community's SoC reference and links to Allwinner documents; support status is time-sensitive |
| [H616 datasheet V1.0](https://linux-sunxi.org/File:H616_Datasheet_V1.0_cleaned.pdf) | Allwinner document hosted by linux-sunxi; SoC capabilities, not SV08 wiring |
| [H616 user manual V1.0](https://linux-sunxi.org/File:H616_User_Manual_V1.0_cleaned.pdf) | Allwinner register/peripheral reference hosted by linux-sunxi |
| [STM32F103VE product and documentation](https://www.st.com/en/microcontrollers-microprocessors/stm32f103ve.html) | ST datasheet, reference manuals, errata, programming documentation for mainboard part |
| [STM32F103CB product and documentation](https://www.st.com/en/microcontrollers-microprocessors/stm32f103cb.html) | ST documentation for toolhead part; different flash capacity from mainboard |
| [TMC2209 documentation](https://www.analog.com/en/products/tmc2209.html) | Analog Devices driver datasheet; current control and UART |
| [ADXL345 documentation](https://www.analog.com/en/products/adxl345.html) | Analog Devices accelerometer datasheet; bus and measurement behavior |

## Software and boot chain

| Reference | Use |
| --- | --- |
| [Klipper documentation source](../upstream/klipper/docs/Overview.md) | Documentation matching our Klipper pin |
| [Klipper configuration checks](../upstream/klipper/docs/Config_checks.md) | Bring-up validation sequence |
| [Klipper bootloaders](../upstream/klipper/docs/Bootloaders.md) | MCU bootloader concepts and target-specific constraints |
| [Klipper configuration changes](../upstream/klipper/docs/Config_Changes.md) | Migration compatibility review |
| [sunxi-tools](https://github.com/linux-sunxi/sunxi-tools) | Maintainer's tools and FEL behavior; pinned locally |
| [U-Boot Allwinner documentation](https://docs.u-boot.org/en/latest/board/allwinner/sunxi.html) | SPL/U-Boot and TF-A requirements for H616; board configuration still required |
| [Moonraker](https://github.com/Arksine/moonraker) | API service source and documentation |
| [Mainsail](https://github.com/mainsail-crew/mainsail) | Web UI source and documentation |
| [BIGTREETECH CB1](https://github.com/bigtreetech/CB1) | Manufacturer's related H616 platform/image reference; not an interchangeable SV08 board specification |
| [Armbian build framework](https://github.com/armbian/build) | Candidate host image build framework; selection pending |
| [Katapult](https://github.com/Arksine/katapult) | Optional MCU bootloader candidate; target/flash layout validation pending |

## Open documentation needs

Find the complete SV08 host/power/storage schematics, BOM and revision history;
identify installed RAM/eMMC/network parts; obtain oscillator and bootloader
evidence; and reconcile thermistor circuitry and probe behavior with vendor code.
The current MCU PDFs do not settle those questions.
