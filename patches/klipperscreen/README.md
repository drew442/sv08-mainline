# KlipperScreen archive version reporting

Patch target: `3791fdf749df20c2a32fc43818749aa9f1754a9f`.
`0001-archive-version.patch` adds an optional root `.version` file before the
existing Git version lookup. The package builder writes the selected short
commit. Unpackaged source trees retain upstream behavior. No printer controls,
networking, display behavior or safety settings are changed.

Gap/reproduction: an archived runtime without Git logs FileNotFoundError and
reports `?` when get_software_version runs, including during Moonraker client
identification. Shipping a Git executable alone would not supply absent history.
The patch follows the source's license. The upstream checkout remains unchanged;
the profile hashes the patch and it is applied only to a build archive.

Validation: test the patched function with a version file while rejecting any
Git invocation; test fallback with an empty file and a mocked Git result. Also
validate the installed runtime against the selected version. See
[test_klipperscreen_archive_version.py](../../tests/test_klipperscreen_archive_version.py).

Upstreaming plan: propose optional archive version metadata support to
KlipperScreen, with these reproductions. No upstream message has been sent.
Retire this patch when a pinned upstream revision provides archive/package
version reporting through a supported mechanism.
