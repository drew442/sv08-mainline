# Public matching-source qualification

SV08 Mainline original code is licensed as described in [the project grant](../../LICENSING.md). Release builders must publish matching project source anonymously and keep the required patches, build and installation inputs available. This check qualifies **project source only**. It does not establish third-party license compliance, vendor kernel/bootloader reproducibility, hardware qualification or overall release readiness.

## Stage notices and provenance

The administrator and printer staging tools include exact LICENSE and LICENSING.md bytes as project-LICENSE.txt and project-NOTICE.txt under /usr/share/doc/sv08-mainline and each staged Cockpit package. project-source.json records the actual Git revision, corresponding source hashes, installed project file inventory, release.json byte hash and project build identity.

Cockpit's ordinary-access **Source & license** control opens the notices and, when checked, the matching immutable archive. It does not request administrator elevation or change printer state. Project build details distinguish the project code revision from the image's display version.

A dirty, unidentified or unmatched development payload is explicitly unqualified. Development staging remains possible without inventing a public source URL. The captured bring-up image builder also reports project_source_qualified=false and overall_release_qualified=false; building an image is not a passing source gate.

For qualified staging, supply --public-source MANIFEST to scripts/stage_admin_ui.py or scripts/stage_printer_ui.py with their normal reviewed fixture/root arguments. The public check runs against prospective payload bytes before writes. Printer overlay reports include notices and provenance in preimages, storage admission and restoration.

## Publish the exact source

Commit and publish the source before qualifying a clean build. The JSON manifest has exactly these keys:

~~~json
{
  "format_version": 1,
  "source_revision": "<full 40-character Git revision>",
  "archive": {
    "url": "https://codeload.github.com/OWNER/REPO/tar.gz/<revision>",
    "sha256": "<SHA256 of the anonymously downloaded archive bytes>"
  },
  "archive_prefix": "REPO-<revision>/",
  "patches": [],
  "build_inputs": [
    {"path": "upstream-lock.json", "sha256": "<exact file SHA256>", "archive_member": true}
  ],
  "install_inputs": []
}
~~~

This is a shape example, not a complete manifest. Each array must exactly cover the corresponding set derived by qualify_project_source.required_inputs from project-source.json's source_files:

- patches: every recorded path under patches/.
- build_inputs: every recorded scripts/ and configs/ path, upstream-lock.json and .gitmodules.
- install_inputs: recorded docs/development/ paths and scripts whose filename contains install, stage, integrate or prepare.

Each item supplies path, sha256 and archive_member:true, or path, sha256 and an independently downloadable immutable HTTPS url. All recorded corresponding source files must match archive members, regardless of these additional coverage arrays. A caller-supplied completeness or availability assertion is not accepted.

Use final HTTPS URLs containing the full source revision or content hash as a path token. Authentication, query tokens, redirects, private/local endpoints, moving branch URLs and unsafe archive entries are refused. Requests use no environment proxy credentials, cookies or authenticated connector. Bounds are 32 MiB downloaded archive, 64 MiB expanded regular files, 8 MiB per member and 10,000 members. Missing source or bounds exhaustion fails qualification; do not bypass the check.

## Qualify the final root

After all project payload, image identity and integration changes, run:

~~~sh
python3 scripts/qualify_project_source.py --root ROOT --public-source MANIFEST
~~~

The command is read-only. A zero exit status and qualified:true receipt establish only scope:project-source-only for that exact build_id and source_revision. It verifies actual installed inventory/notices/release provenance, anonymously downloads pinned source and inputs, then rechecks the root for drift. Preserve the receipt, manifest, source revision and source-bound test evidence with the release records.

A staging-time success is insufficient if subsequent integration changes files or release.json. Re-stage matching provenance and rerun the final gate. If release.json contains project_source_revision, it must match; the image display version alone is not treated as the project revision. Missing release provenance, changed files/notices, stale release bytes, unavailable archive, wrong hashes or incomplete input coverage must refuse source qualification.

This gate does not modify runtime update admission or certify an entire image. There is currently no unified supported-release publication entrypoint: release coordinators must run this mandatory final-root gate explicitly and retain its receipt before describing project source as qualified. Third-party corresponding source/notices and captured vendor artifacts remain separate obligations.
