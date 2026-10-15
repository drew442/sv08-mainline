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

The checked-in supplemental evidence currently resolves 60 of the historical 69
records. Nine remain explicit blockers in the JSON; selected-software packaging
continues to fail. The JSON retains original text bytes; generate the plain-text collection with
--text-output or release preparation. The collection does not establish that
those nine packages are licensed for redistribution.
