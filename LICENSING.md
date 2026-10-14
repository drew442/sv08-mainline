# SV08 Mainline licensing

Project-owned original code in this repository is licensed under the GNU Affero General Public License, version 3 or (at your option) any later version: **AGPL-3.0-or-later**. The owner selected this policy on 2026-10-14. See [LICENSE](LICENSE) for the complete version 3 license text.

You may use, modify, fork, rename and redistribute covered code, including commercially, under that license. Covered distributed derivatives retain the applicable copyleft and corresponding-source obligations. Modified network-facing versions must comply with AGPL section 13. There is no additional prohibition on renamed forks, commercial use or private modifications.

The program is provided without warranty, including the implied warranties of merchantability and fitness for a particular purpose, to the extent permitted by applicable law. See LICENSE for the terms.

## Scope and third-party material

This grant covers independently owned original project code, including original controllers, interfaces, build tooling, tests and the original admission extension. It does not relicense upstream submodules, downloaded dependencies, embedded third-party material, copied upstream code, upstream-derived patches or files carrying their own licensing terms. Preserve their copyright, attribution and license notices. Independently owned original documentation uses this project license unless otherwise marked; quoted or reproduced third-party material retains its applicable terms.

A root license does not make every program in a printer image AGPL. Separately aggregated programs retain their own licenses. A combined or derivative work must satisfy all applicable licenses; review integration boundaries rather than assigning a license solely from its directory.

The pinned Klipper source is GPLv3. GPLv3 section 13 permits combining GPLv3-covered code with AGPLv3-covered code: the GPL-covered portion remains GPL-covered, while AGPL network-interaction requirements apply to the combination. Our original admission extension uses the project grant; this does not change Klipper's license or qualify every possible plugin integration. Existing source hashes and historical license inventories remain historical observations, not evidence to rewrite retrospectively.

Authoritative references: [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html), [GNU GPLv3 section 13](https://www.gnu.org/licenses/gpl-3.0.html#section13), and [GNU licensing guidance](https://www.gnu.org/licenses/gpl-howto.html).

## Public source release policy

For every project release, publish the complete corresponding source publicly at no charge, tied to the exact release/artifacts. Include project modifications, applicable upstream pins and patches, and the scripts/instructions needed to build and install the covered software. A moving branch or a link to a different version is insufficient. Respect each dependency's separate corresponding-source and notice obligations; a dependency inventory alone is not the source offer.

Network-facing releases must provide a prominent way for users to obtain the corresponding source, including modified versions when AGPL section 13 applies. Source availability is a release acceptance condition; do not describe a release as qualified until the exact source and applicable offers have been checked.

Do not publish credentials, signing keys, personal printer data or private calibration/configuration as part of a source release. Publish non-secret templates and required build inputs instead.

This public-publication rule is our own release policy. Standard AGPL does not require every private modification to be published to the general public; its downstream legal obligations are those in LICENSE. Recipients and relevant network users retain the rights it grants.

## Contributions

Contributions to project-owned code are accepted under AGPL-3.0-or-later unless a different arrangement is explicitly agreed before acceptance. Contributors retain their copyright and must have the right to contribute the material. Third-party code must include its provenance and applicable notices; do not remove existing terms or infer ownership from a commit author.

New independently owned source files should identify `SPDX-License-Identifier: AGPL-3.0-or-later` where the file format supports comments. Existing third-party identifiers must be preserved. A repository-wide header rewrite is not required to apply the root grant.
