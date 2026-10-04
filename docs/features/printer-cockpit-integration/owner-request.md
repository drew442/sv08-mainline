# Owner request — 2026-10-04

After the installed theme correction, the owner reported:

> the printer hardware section still feels like its external or bolted on. it should be seamlessly integrated into cockpit

This authorizes replacing the separate top-level navigation experience with a
section in the existing authenticated SV08 Cockpit interface. Preserve the
accepted board/component configuration behavior and saved data. Existing authority
for routine development, reviewed installation and publication continues. Physical
filament/probe checks and fine calibration remain deferred.

The previous finite `sv08-printer` asset/helper package may remain an internal
packaging boundary; it must no longer require a separate visible shell, duplicated
session controls or leaving the main navigation. This supersedes the previous
proposal's ordinary top-level link as the required user experience. It does not
reopen H12 or authorize configuration activation, heaters or motion.
