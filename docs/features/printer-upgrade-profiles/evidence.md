# Named upgrade profile source and offline evidence

Coordinator self-validation. This is source/offline evidence, not installed
acceptance, original-SV08 adaptation, mainline module firmware compatibility or
heater/motion commissioning.

The exact owner-selected [Funssor kit](https://funssorlab.com/products/sovol-sv08-3d-printer-upgrade-hotbed-complete-kit-with-3d-printed-parts-design-by-nadircn3d-10mm-riser-heated-bed-upgrade-kit-120-240v-silicone-heater-01mm-flat-aluminum-bed)
page identifies an 8mm aluminum assembly, advertised 120°C heating capability and
135°C thermal fuse. Its text/wiring figures do not identify the thermistor. The
named profile uses the original SV08 bed interface reference, clears the old
factory curve and PID, and retains board-reference bias, power and software bounds
(105°C cutoff). These are reference settings, not newly measured safe kit limits.
The hardware choice saves, but complete generation still needs an explicitly
identified sensor. No Generic3950 assumption is borrowed from another Funssor kit.

Sovol's [manufacturer repository](https://github.com/Sovol3d/SV08MAX/blob/68c28ea4ef5a81279d69c0e7d3b6433f0945192b/home/sovol/printer_data/config/chamber_hot.cfg)
is pinned at `68c28ea4ef5a81279d69c0e7d3b6433f0945192b`. The
[reference snapshot](../../../catalog/printer/sources/sovol-sv08-max/chamber-reference.cfg)
retains exact line numbers and settings with only its sample CAN UUID replaced
by a comment. [Provenance](../../../catalog/printer/sources/sovol-sv08-max/provenance.json)
records the original and snapshot hashes, URL, revision and transformation.
This small reference is not a new upstream checkout/submodule; existing gitlinks,
upstream-lock.json and source/toolchain identities are unchanged.

The module profile records PA4 room input, PA5 heater input, PA0 heater output,
EPCOS sensor definitions with 20000-ohm reference bias, watermark control and 65°C
reference cutoff. It adds a separate `chamber` MCU role and typed heater instead of
mapping the module onto mainboard GPIO. CAN identity is empty and serial transport
is refused. Generator version 5 qualifies pins as `chamber:...`, emits one generic
heater and keeps upstream heater verification. Vendor relaxed verification and
macros are not emitted. No physical MCU identity, clock or firmware is inferred.

Sovol's [official download page](https://www.sovol3d.com/pages/download) links the
SV08 MAX chamber manual. The V1.1 manufacturer manual, also available through its
[forum attachment](https://forum.sovol3d.com/t/installation-guide-video-of-sv08-max-auxiliary-heating-module/9224),
was read with the installed PyMuPDF environment and its wiring page rendered and
visually checked. It specifies SV08 MAX, CAN2 and the MAX installation path; this
does not establish an original-SV08 CAN connection. The owner was asked for the
adapter/interface and supplied Funssor thermistor specification. Those remain
pending, as do actual firmware compatibility and physical installation checks.

## Actual checks

- `python3 -m unittest discover -s tests -p test_printer_configuration.py`:
  41 tests passed, including source/hash/line provenance, legacy drafts, transport
  metadata, separate MCU pins, unknown identity, collisions, forbidden mainboard
  substitution, full-mode emission and sensor-mode refusal.
- `python3 -m unittest discover -s tests -p test_stage_printer_ui.py`:
  11 staging/preservation tests passed.
- Chromium 1208 and Node 22.23.2, with the real disposable Store via
  `tests/test_printer_browser_fixture.py` and `tests/printer_browser.mjs`:
  complete existing browser regressions plus named Funssor incomplete save/reload,
  module checkbox add/save/reload/remove, empty CAN identity, 20000-ohm bias,
  65°C reference cutoff and unrelated-device preservation passed. See the
  [sanitized browser receipt](browser.json).
- Generated full three-MCU fixture reached actual Klippy API `info.state=ready`
  in pinned mainline `f0892d82b0f1c1228454f09eb508eddde2250f4b` file-output mode.
  Synthetic shared STM32F103 protocol dictionaries validate syntax only; they do
  not identify the chamber MCU or prove firmware compatibility. No CAN interface,
  physical MCU, heater or motion was accessed.
- Node syntax, catalog/draft JSON Schema, relevant document links, complete stable
  diff and whitespace checks passed.

The module's stock exhaust fan is a separate existing component. No guessed module
fan pin, arbitrary config template, output activation or service restart was added.
The source UI/helper/catalog must still be delivered together to the installed
host. The older simplified-UI evidence is historical to its source revision.

Manual SHA256: `5731edbff7a378b4acf37c43474cd27a644b293d297a7f2f5b77bcc0184f390b`.
Private file-output receipt SHA256: `7890c9663606d7c398e6c872d398a86736e3be4c6073f4a8740fcc0818ec0829`.
