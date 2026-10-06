# Factory SV08 definitions installation

Source `80c1a52`, integrated on main at `c672811155907b49247e8687f4ef8a83ccf81204`, installed on the spare eMMC A target on 2026-10-06. The independently reviewed, hash-bound overlay updated ten runtime/catalog/UI files, including the complete 24-device factory assembly.

[Installation receipt](installed.json) records installed hashes, review inputs and observed closure. Authenticated Chromium acceptance on the actual ARM64 Cockpit page passed: full factory preview (including the accelerometer), cancellation, seven component cards, factory choices, separate Definition sources navigation, history/reload, logical connections and responsive widths 390/1024/1440. Hardware state remained unchanged.

Root and boot remain read-only, data writable, PSU off, service masks preserved, live printer configuration absent, and the installer unit inactive with MainPID zero. The rollback copy is `/data/sv08/printer-factory-definitions-backup-20261006`.

This is software installation and read-only acceptance, not hardware commissioning or a printing release. No hardware selection was saved, generated configuration applied, heater/motion activated, MCU flashed or printer service started. Private controller identities and measured calibration remain local; vendor pressure-probe auto-Z behavior is a separate commissioning workflow.
