# My printer definition source

A starter repository for the **SV08 Mainline Definition sources** page. The
included board, bed, assembly and behaviour records are source-backed SV08
reference examples. Replace the catalogue identity and describe your own hardware
before publishing. Downloading or browsing this template does not configure a printer.

## Start your repository

1. Extract this ZIP. Use the contents of `printer-definition-repository/` as the
   root of a new public GitHub repository.
2. Edit `catalog.json`: choose a unique `catalog_id`, catalogue `name` and
   `publisher.name`. Keep `catalog.json` at the repository root.
3. Edit/copy the JSON examples in `definitions/`. Set each definition's unique ID,
   version, category, exact product/revision, documented settings and source links.
   Local dependencies omit `source` and refer to an exact ID/version. The assembly
   example shows how to combine component and board definitions.
4. Refresh both dependency digests and the catalogue index:

   ```sh
   python3 tools/update_catalog.py
   ```

5. Validate with a checkout of SV08 Mainline (replace the final path):

   ```sh
   python3 scripts/printer_definitions.py validate /path/to/your-repository
   python3 scripts/printer_definitions.py bundle /path/to/your-repository > bundle.json
   ```

   Run these two commands from the SV08 Mainline checkout. The included refresh
   helper uses only Python's standard library; it updates hashes and detects local
   dependency mistakes, but does **not** replace the full hardware/schema validator.
6. Commit and push your repository. On the printer, open **Definition sources**,
   enter `https://github.com/YOUR-NAME/YOUR-REPO`, preview it and add the catalogue.
   You can instead import `bundle.json` through **Import bundle** to test it offline.

## Repository layout

- `catalog.json`: publisher details and indexed definition files.
- `definitions/board.json`: documented controller mapping example.
- `definitions/bed.json`: components, connections and sensor-curve example.
- `definitions/assembly.json`: dependencies composing a kit.
- `definitions/behaviour.json`: explicit no-additional-check example.
- `fixtures/installation.json`: disposable software preview input, not a real
  printer identity or commissioned configuration.
- `tools/update_catalog.py`: standalone index/dependency refresh helper.
- `LICENSE`: licence notice for the supplied examples.

## Editing and publishing

When changing an already published record, bump its version and update local
references to that version before refreshing hashes. Published versions are
immutable. External dependencies with an explicit `source` retain their supplied
pinned digest; update them deliberately with their publisher's version/digest.

Keep instance MCU identities, measured calibration and private data out of the
repository. Preserve source attribution and the GPL-3.0-or-later terms for copied
examples. Cite exact hardware documentation; the reference values in these files
are examples, not defaults for arbitrary replacement hardware.

Public format and creator tooling:
https://github.com/drew442/sv08-mainline/blob/main/docs/development/printer-public-format.md
