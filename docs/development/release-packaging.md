# Preparing exact-artifact release evidence

`scripts/prepare_release.py` prepares a deterministic directory of evidence for a
named immutable artifact. It does not publish, deploy, copy the large image, or
qualify a printing release. Keep the artifact alongside the evidence and verify
its SHA256 against `release-manifest.json` before transferring or using it.

Run against a trusted disposable regular image on a coordinator development host
with `losetup`, `mount`, `umount`, `findmnt`, `dpkg-deb` and read-only ext4/squashfs
support. Managed inspection requires mount privileges. The tool never executes
image programs or package maintainer scripts. It creates temporary read-only loop
mounts, disables ext4 journal replay, verifies their kernel backing/offset/length,
and cleans up the nested usr mount before the root and loop devices. No writable
image mount or printer access is involved. An optional existing `--root` on the
inventory tool must pass the same kernel mount verification; a staging directory
cannot substitute for the artifact.

```sh
sudo python3 scripts/image_license_inventory.py \
  --image /path/to/final.img --scratch /path/to/disposable-parent > image-inventory.json
sudo python3 scripts/prepare_release.py \
  --image /path/to/final.img --public-source /path/to/public-source.json \
  --inventory-inputs /path/to/license-inputs.json \
  --scratch /path/to/disposable-parent --output /path/to/new-release-evidence
```

The default `selected-software` profile runs the fixed image, public project source
and selected software notice checks. Missing, stale or failed prerequisites refuse
packaging. Arbitrary JSON success receipts are not accepted. The license inputs
have the existing [inventory tool](../../scripts/license_inventory.py) format;
`mainsail.supplemental_notices` can add a `{root,path,sha256}` pin to the supplemental
notice JSON produced below. Every selected application Debian package must match
an installed package identity and its actual usr payload in at least one software
partition. Non-usr package members are explicitly counted outside that binding.
Selected configuration bytes must belong to the image's matching project source.
Missing installed package databases or unresolved selected notices fail this scope.
This does not assert that the selected inputs cover every installed dependency,
that supplier source archives were rebuilt, or that boot firmware is licensed for
redistribution.

For a narrower project-source evidence package, explicitly select
`--profile project-source` and omit `--inventory-inputs`. This still inventories the
actual image and invokes the existing [anonymous public matching-source
qualifier](public-source-releases.md) inside every software root. It makes no
selected software notice claim. A UI-only source fixture without a dpkg database
can qualify this scope, with that missing coverage recorded explicitly.

The image tool supports raw ext4, DOS primary partitions and the existing validated
GPT layout. GPT root A, root B and recovery software filesystems are inspected
individually. Every partition has an exact byte hash; boot/data partitions remain
opaque, without enumerating their contents. Only usr, bin/sbin/lib/lib64 software and dpkg metadata
are enumerated. Configuration, credentials and user data are excluded. Notices,
actual package names/versions/architectures, usr squashfs hashes, project provenance,
and missing/unknown coverage are reported. Invalid project provenance and absent
package databases remain visible in inspection reports; the corresponding release
checks still refuse them. Historical image inspection is evidence about those
historical bytes, not qualification of current source.

Outputs are canonical JSON with no timestamps, transient mount paths or caller
success assertions. The package contains the public source manifest, actual image
inventory, scoped report, and (for selected software) software inventory, installed
application bindings and supplemental notices. The release manifest binds every
output hash, source revision and artifact identity. Output directories must not
already exist. Failed checks do not produce a package. An unchanged successful
input set produces identical output bytes.

Both profiles always report `overall_release_qualified:false` and
`hardware_qualified:false`. Hardware, recovery execution, third-party corresponding
source completeness, legal compliance, vendor source reproduction and full
reproducibility remain separate requirements. The report states exactly which
software/source checks ran; it cannot turn inventory unknowns into release approval.

## Supplemental NPM notices

```sh
python3 scripts/resolve_npm_notices.py \
  --research /path/to/retained-upstream-evidence.json \
  --output /path/to/npm-supplemental-notices.json \
  --text-output /path/to/npm-notices.txt
```

Research inputs retain exact NPM tarballs and public registry/source responses.
Transport records distinguish anonymous fetches from public GitHub API responses
retrieved through the coordinator's existing development authentication after
anonymous rate limits. No credentials are stored in the notice evidence.
The resolver validates archive SRI and package identity, response/text SHA256,
exact-version registry identity, upstream repository and commit mapping, and source
notice scope. The input must exactly cover all 69 historical declaration-only
records in the retained baseline, including their original archive hashes. Exact registry gitHead can identify a generated platform package's
source commit even when its package.json is generated at publication. Without
package-directory proof only a repository-root notice qualifies. Without gitHead,
a VERSION/vVERSION tag must resolve to the commit and source package name/version
must match. Sibling package notices never establish coverage automatically.

The portable JSON embeds original UTF-8 upstream response and notice bytes with
URLs and hashes. Text output preserves the upstream wording and authorship.
Unresolved records have concrete reasons and cause a nonzero exit; no grant or
SPDX license text is invented. The inventory tool independently validates the
supplemental records against the selected lock, archive and version. This is
factual provenance and notice coverage, not legal advice or an upstream license
change. Upstream archives remain unchanged.

Additional explicit mappings preserve their limits: a package-generated
`buildInfo.commitSha` plus the exact version tag can identify generated releases;
complete shipped executable-source byte equality can bind a source snapshot;
and an authoritative whole-tree comparison permitting only addition of LICENSE
can bind a later author notice without changing the inspected release code. These
records retain the later notice provenance and do not assert retroactive legal
effect. An upstream package-name alias requires the exact registry commit and
complete shipped code equality, and remains visible as a metadata discrepancy.
A pinned source README may explicitly reference an external author notice document;
the actual fetched document and source reference are separately hashed and retained.

The checked-in supplemental evidence resolves 60 of the historical 69
records. Nine retain their original missing author-notice facts in that historical
JSON. Current selection accounting separately measures removals, replacements and
the explicit standard-terms acceptance below. The JSON retains original text bytes; generate the plain-text collection with
--text-output or release preparation. The collection does not establish that
those nine packages are licensed for redistribution.

## Historical gaps and changed dependency selection

The original 69 records remain fixed historical evidence. A new selected lock can
remove or replace a dependency without granting rights to its old version. Run
`resolve_npm_notices.py --selection-inputs INPUTS --output REPORT` to create a
separate accounting report. INPUTS contains file pins `{root,path,sha256}` for
`selected_lock` and `supplemental_notices`, plus `replacement_archives` keyed by
original dependency path. The selected lock must match the current Mainsail
profile, and the supplemental input must match the retained notice set. A
replacement archive must match the actual selected version and SRI and contain
real embedded notice text. The report preserves original identity, archive hash
and notice status, and distinguishes current retention, removal and verified
notice-bearing replacement. Remaining selected gaps cause a nonzero exit.

The revision-5 Mainsail patch replaces throttleit 1.0.1 with notice-bearing 2.1.0
through a scoped npm override and removes an unused compiler edge, pruning
de-indent. The original 60 notice resolutions and nine unresolved historical
facts remain unchanged. That historical selection had two measured remediations and seven remaining
author-notice gaps. Later source-bound replacements are accounted for by the
current selection report; these changes do not make a release qualified.


## Explicit standard LGPL terms for gcodeviewer

For exact `@sindarius/gcodeviewer` 3.7.18, the owner accepts its SRI-verified
`package.json` declaration `LGPL-3.0-or-later` together with distributor-provided,
unmodified standard SPDX terms. This exception does not infer rights for other
packages. The [configuration](../../configs/host/npm-standard-license-texts.json)
pins the name, version, SRI, archive and package metadata hashes, license identifier,
and immutable SPDX source revision/URL and full text hash. The
[standard document](../licensing/standard/LGPL-3.0-or-later.txt) includes both the
LGPL supplement and incorporated GPL3 terms. Its FSF document copyright is not
attribution for gcodeviewer. No author attribution is invented.

Add `mainsail.standard_license_texts: {root,path,sha256}` to inventory inputs,
pointing to that configuration. The inventory independently verifies the original
archive's SRI, exact metadata declaration and immutable text/source anchors.
`notices` and `supplemental_notices` stay empty for this package; the separate
`standard_license_texts` field and `dependencies_with_distributor_standard_terms`
count distinguish acceptance from supplier notice recovery. Without the explicit
input, this dependency remains a declaration-only gap and packaging refuses it.
Unknown packages, altered records, duplicate/extraneous entries, missing documents,
and text or source pin tampering are refused.

For selection accounting, add the same `standard_license_texts` file pin at the
input root and `standard_license_text_archives`, a map with exactly the key
`node_modules/@sindarius/gcodeviewer` and a `{root,path,sha256}` pin to its original
supplier archive. The resolver verifies actual SRI/archive/package metadata bytes.
Its selection status becomes `accepted-distributor-standard-terms`, while the
historical `unresolved-author-notice` status and all 60 supplemental notices remain
unchanged. This acceptance clears only that selected gap.

Selected-software evidence exports the verified full text as
`LGPL-3.0-or-later.txt` and its exact configuration as
`npm-standard-license-texts.json`. The release manifest hashes both files; export
also rechecks the immutable pins and their agreement with the qualified inventory.
The project-source profile is unchanged. This records the owner-approved source
facts and terms, not an upstream license change, recovered author notice, new grant
or legal compliance assessment.

Focused tests can use a retained immutable original archive without downloading:

```sh
SV08_GCODEVIEWER_ARCHIVE=/path/to/original-gcodeviewer-3.7.18.tgz \
  python3 -m unittest discover -s tests -p test_license_inventory.py
SV08_GCODEVIEWER_ARCHIVE=/path/to/original-gcodeviewer-3.7.18.tgz \
  python3 -m unittest discover -s tests -p test_resolve_npm_notices.py
SV08_GCODEVIEWER_ARCHIVE=/path/to/original-gcodeviewer-3.7.18.tgz \
  python3 -m unittest discover -s tests -p test_prepare_release.py
```

Without that environment variable, actual supplier archive cases are explicitly
skipped; portable approval/text/identity rejection tests still run. The release
unit fixture qualifies real supplier bytes and writes the actual evidence files,
while mocking image inspection and unrelated full inventory generation. Actual
image inspection and full release execution remain coordinator integration checks.
