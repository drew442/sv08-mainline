# Creator-published printer definitions — design proposal

**Project:** sv08-mainline
**Status:** Owner-selected implementation requirements; the public format is draft until runtime/fixture acceptance
**Revision:** 0.2 — 6 October 2026
**Companion:** [Printer hardware page design brief](printer-hardware-page-design.md)
**Inspected repository:** `main` at `11912e05c7a14650cc7a0c486e40482da9241760`

## 1. Decision and product goal

Support **definition sources**: GitHub repositories containing one or more hardware definitions in a published, versioned format. A creator, manufacturer or independent contributor can publish a source without opening a pull request against sv08-mainline. A printer owner adds its repository once; supported definitions then appear alongside built-in choices in the ordinary component selectors.

Built-in, creator-published and locally authored definitions use the **same public format and composition engine**. Origin affects attribution and update handling, not whether a second UI or bespoke generator is required. Existing built-ins may need an adapter during migration, but there must not be a permanent privileged definition language available only to the project.

The intended experience is:

> Add creator repository → choose its upgrade in the relevant component section → adjust any installation-specific details → review → apply through the normal configuration workflow.

Adding a source makes choices available. It does not select its upgrades, replace another author's definitions, install software, write live configuration or operate the printer. Neither adding a repository nor choosing a previously supported preset requires central project approval.

This is a distributed catalogue, not a marketplace. Public GitHub repositories are the first transport, not part of a hardware definition's semantics. Leave room for local bundles and other Git hosts without building a general package manager now.

## 2. User experience inside Cockpit

### 2.1 Definition sources

Keep **Components**, **Connections** and **Changes** as the three primary local views. Add a secondary **Definition sources** action to the Printer hardware toolbar, outside Advanced. It opens an ordinary page-local panel or subview in the existing shell. A back action restores the component view and its unsaved selections.

Use a compact table, existing colours and simple source/link icons. Do not introduce vendor logos, remote images or a shopping page. The following is a text wireframe, not an additional browser render:

```text
Printer hardware / Definition sources

[Add repository]  [Import bundle]                 [Check for updates]

Source                  Origin                State       In use
SV08 Mainline           Built-in              Available       4
Creator's SV08 kits     creator/printer-kits   Available       2
Workshop variants      workshop/sv08-parts    Update ready    0

Source details: repository • catalogue version • pinned revision
Actions: View definitions • Review update • Disable • Remove
```

Example names/counts are illustrative. Neither CN3D nor another named manufacturer is claimed to publish this format today.

**Add repository** normally asks only for a GitHub repository URL. Discover `catalog.json` at its root and inspect the default branch. Advanced options select a different catalogue path and branch, tag or exact commit. Accept a supported manifest-file URL as a convenience without guessing ambiguous branch/path boundaries.

Preview the resolved owner/repository, catalogue name, definition count, supported and unsupported entries, declared maintainer and licence. Let the user confirm **Add source**. Fetching and checking the source must not require a GitHub account for a public repository; GitHub documents unauthenticated public contents access [G1]. Rate limits still require caching, bounded requests and useful retry messages [G2]. Private repositories and credential setup can follow later.

### 2.2 Unified component choices

Show one searchable list per component category. Each result has the exact upgrade/variant, source and version, plus any relevant compatibility/input status. A source filter is available but is not required for everyday use. Adding a source must not change the order or identity of an already selected preset.

Separate **source origin** from **evidence**. Use labels such as “Built-in”, “From creator/printer-kits” and “Local definition”; show “Maintainer reports testing on …” separately. An author-supplied name or `tested` flag does not earn a system-generated manufacturer-verification or safety badge. Likewise, shipping a preset with the project does not certify every installation.

The selection's details show its guide, author, definition revision, unresolved questions and local overrides. Two presets with the same product name remain separate, identifiable choices. An external preset can be chosen instead of a built-in one through an explicit replacement preview; source ordering never overrides the selected one.

### 2.3 Updating and removing a source

**Check for updates** discovers candidate source revisions. **Update catalogue** makes a validated revision available to browse. **Update selected preset** stages a change to the printer draft. **Apply configuration** remains the final, separate operation. The UI can combine the middle steps into a guided review, but the underlying states must remain distinct.

Show the impact on selected definitions, their dependencies, local overrides, thermal/motion behaviour and calibration. Unselected new presets need not trigger a printer-level confirmation. Metadata-only changes should not require a hardware commissioning ceremony.

Disabling a source stops discovery and new selections. Removing it removes the subscription, not the installed hardware or its retained definition snapshot. Keep everything referenced by saved drafts, active configuration or retained restoration points. Offer **Remove upgrade** separately, with the normal component-change review. Warn if a retired definition remains selected; do not silently uninstall it.

## 3. Creator workflow and publication layout

Publish a small starter repository, a schema reference, examples and a validator. A contributor should edit definition data, not application code, and should not need a printer connected merely to check syntax or generate a test candidate.

The basic contribution path is: copy the starter; describe the upgrade and its guide; run validation/preview; publish the repository; share its URL. A tag or GitHub release is recommended for stable releases but is not mandatory for initial use. The tool should generate the index and file hashes rather than ask an author to maintain duplicate metadata by hand.

Proposed layout:

```text
creator-printer-definitions/
├── catalog.json                   # Entry point: publisher, format and index
├── definitions/
│   ├── bed-assembly.json
│   ├── toolhead-assembly.json
│   └── multi-colour-bundle.json
├── fixtures/                      # Optional for import; strongly encouraged in CI
│   ├── standard-installation.json
│   └── alternative-toolboard.json
├── README.md                      # Supported builds, guides and limitations
├── LICENSE                        # Distribution terms for the definitions
└── .github/workflows/validate.yml  # Optional creator-side validation
```

Only indexed data and explicitly referenced, supported assets enter the printer's cache. A build guide, image collection, CI script or other unrelated file in the same repository is not downloaded as runtime content. One definition is a valid collection; a large creator repository need not be reorganised if a catalogue lives in a selected subdirectory.

**Published representation: JSON, validated with JSON Schema Draft 2020-12.** Allow optional YAML authoring through creator-side tooling that emits the same strict JSON. JSON-only repositories need no build step. This avoids requiring YAML tooling on the appliance while leaving authors a comment-friendly format. The optional YAML path must reject duplicate keys, custom tags and non-JSON values rather than silently coerce them.

Provide editor completion, human-readable errors and a local preview using the same semantic validator as the runtime. A later **Export as reusable definition** action can convert a local structured customisation into a starter definition: preserve source attribution, ask for hardware scope and remove private serials, CAN UUIDs, hostnames and user calibration. Replace necessary instance-specific values with required inputs; never replace them with invented defaults.

A creator's CI runs in the creator's environment. The printer does not execute repository workflows or use a green CI badge as a substitute for its own validation.

## 4. Public schema contract

### 4.1 Publish a contract, not just an internal storage schema

The inspected project already has a Draft 2020-12 catalogue schema and a documented contribution path for existing device kinds [P1, P2]. That is a useful base, but the public format should not expose incidental storage envelopes, private MCU identity fields or board-first UI assumptions.

Publish machine-readable schemas, field documentation, semantic rules, positive/negative examples, compatibility policy and a validator together. Proposed schema files include:

```text
schemas/printer-definitions/v1/
  catalog.schema.json
  definition.schema.json
  component.schema.json
  board.schema.json
  assembly.schema.json
  behaviour.schema.json
  connection.schema.json
```

These are proposed paths, not files created or URLs published by this design document. Keep the public format at a draft version while the composition model is being exercised. Before declaring stable v1, round-trip representative built-in and third-party definitions through the actual validator/generator. The public definition version is distinct from the existing internal draft schema version.

JSON Schema supplies structural validation; composition and hardware constraints need a semantic validator. Draft 2020-12 is a suitable published dialect [S1]. Where schemas compose common fields and kind-specific fields, close the completed object appropriately rather than placing `additionalProperties: false` where it prevents intended extension; JSON Schema documents this distinction and `unevaluatedProperties` [S2].

### 4.2 Catalogue envelope

| Field group | Proposed responsibility |
| --- | --- |
| `$schema`, `format_version` | Public catalogue format and supported version. Not the JSON Schema dialect itself. |
| `catalog_id`, `name`, `description` | Stable collection ID and plain-text display information. |
| `publisher`, `homepage`, `issues`, `license` | Attribution, support and distribution terms; declarations, not proof of identity. |
| `definitions` | Explicit index of relative file paths, local IDs, versions and SHA-256 content digests. Generated by tooling. |
| `extensions` | Bounded, namespaced, non-behavioural metadata. |

The source URL and trusted source identity come from the user's selection and fetched repository metadata, not from a publisher-controlled field inside the manifest. The manifest cannot claim to be `builtin` or silently redirect updates to another repository.

### 4.3 Definition records

| Field group | Required meaning |
| --- | --- |
| `id`, `version`, `kind` | Stable local ID, immutable published definition version and a supported record kind. |
| `name`, `description`, `aliases`, `category` | Search and display metadata. Use a built-in icon identifier; no publisher HTML/CSS/JavaScript. |
| `hardware` | Exact product/board revision and supported variants, including what is not established. |
| `compatibility` | Tested/declared printer and board scope, required runtime capabilities and relevant software constraints. “Unknown” differs from “incompatible”. |
| `inputs` | Typed installation choices with labels, units, documented defaults, allowed values and conditions for being required. |
| `components`, `connections` | Semantic device roles, board/connector bindings and capabilities; not copied host-specific serials. |
| `settings`, `behaviours` | Typed configuration contributions and named behaviour hooks with documented semantics. |
| `dependencies`, `conflicts` | Explicitly qualified definition references and combination requirements. No implicit global-name lookup. |
| `sources` | Guide/reference ID, URL, revision or content hash where available, and section/page/line locator. |
| `calibration` | Dependencies that invalidate calibration and required commissioning steps, not someone else's measured results. |
| `support`, `tests`, `extensions` | Maintainer support, evidence declarations and bounded metadata. |

Use a common envelope with discriminated, documented record kinds: **component**, **board**, **assembly** and **behaviour**. An assembly can own several components and span several UI categories. Behaviour records compose supported operations/hooks; they are not a way to introduce Python, JavaScript or a custom evaluator.

For standard documented installations, most creators should only need an assembly that references existing components, board mappings and behaviour hooks. A new bed supplier should not have to copy an entire mainboard definition. A new board can be data-only when it uses supported controller/driver/circuit types; a genuinely new driver requires application support.

Reuse source references by ID. Require provenance for operational defaults and allow evidence to apply to a well-defined group of fields; do not demand repeated URL/hash boilerplate for every display label. Distinguish a guide's documented value, a derived mapping, a user-entered override and an unknown value. Publication tooling can populate hashes and pinpoint missing coverage.

### 4.4 Extensibility rules

Extensible does not mean “accept arbitrary new fields and hope they are harmless.” Use three paths:

| Extension | Treatment |
| --- | --- |
| Another component, board mapping, assembly or variant using supported kinds | Data-only contribution; no sv08-mainline pull request required. |
| Additional descriptive metadata | Namespaced entry in `extensions`; retained but never used to change output or safety decisions. |
| New operational meaning, output adapter, device driver or macro execution capability | Declare a required capability and minimum supported format/runtime. Unsupported printers show an explanation and do not generate an approximation. |

Unknown operational fields, record kinds and required capabilities are errors for generation, not fields to ignore. An unsupported entry can remain visible as unavailable without making unrelated, valid entries in the source unusable. Invalid source identity/index structure prevents that catalogue revision from being accepted at all.

The runtime chooses its **bundled, trusted schema** from the supported format/version. It never downloads and trusts whatever schema a repository's `$schema` points at. External references, custom validation code and runtime schema downloads are not permitted. JSON Schema's `$schema` and dialect concepts are documented separately from this application policy [S3].

Use bounded conditions such as equality, membership and capability checks for variant forms. Do not embed an expression language with arbitrary evaluation just to hide a dropdown. Declarative input constraints are still checked against application-enforced limits; a publisher cannot enlarge a hardware/runtime limit by increasing an input's `maximum`.

## 5. Illustrative authoring shape

This is an abbreviated **design example**, not a schema-valid, usable bed definition. The named values below are proposed semantic fields, not verified kit settings. No cutoff, sensor curve, pin or levelling threshold is fabricated.

```yaml
# Optional creator-side YAML; published content would be JSON.
format_version: "0.1"
kind: assembly
id: sv08-bed-upgrade
version: "0.1.0"
name: "Example creator bed assembly"
category: bed
hardware:
  product: "Exact kit and revision to be supplied by its author"
compatibility:
  requires_capabilities:
    - klipper.heater_bed.v1
    - levelling.temperature_condition.v1
inputs:
  supplied_sensor:
    type: component_reference
    role: bed.temperature_sensor
    required: true
components:
  - role: bed
    # Reference a supported heater/assembly type and documented defaults.
connections:
  - endpoint: bed.temperature
    binding: guide_default_or_user_override
behaviours:
  - hook: levelling.preconditions
    # Author must supply sourced comparison/phase/threshold/timeout semantics.
unresolved:
  - exact_sensor_identity
  - verified_software_temperature_limit
  - guide_derived_levelling_condition
```

An actual completed definition would reference established sensor/board definitions, supply sourced parameters and declare precise compatibility. The user's **Connections** override would remain in the printer instance, not alter the downloaded file. A bundle can reference a bed, toolhead and feeder from the same catalogue without duplicating their data.

## 6. Identity, dependencies and reproducibility

Give each accepted source a canonical local identity based on the provider, stable repository identity and catalogue root. Keep the human-readable owner/repository alongside it. Source roots and local definition IDs are case/encoding-normalised according to a documented rule, not arbitrary publisher aliases.

A selected definition is identified by **source + definition ID + definition version + content digest**. Internally retain the exact repository commit and the entire dependency closure. Namespaced display references can resemble `creator/printer-kits::bed-assembly@1.2.0`; this is explanatory notation, not a promise about a final URI grammar. Reserve `builtin` for application-supplied content; external manifests cannot assign that origin to themselves.

Do not resolve a dependency against another source merely because its ID matches. Same-source references are explicit; cross-source references identify the intended source. Missing sources are offered for addition, never silently subscribed to. In v1 prefer exact dependency versions, one chosen version per definition identity per resolved printer plan, and explicit incompatibility errors. Use semantic device roles and instance IDs so an assembly can contain several instances of the same component.

Pin the selected closure to hashes in the local printer plan. This includes built-in dependencies and combination policies: an OS/application catalogue update must not silently replace their behaviour underneath a third-party preset. Different dependency versions within one source may coexist in storage for different saved plans; a conflicting single-plan requirement is a resolution error.

Reject cycles and conflicting ownership of a device, configuration key, macro, physical resource or required behaviour. A name collision is not resolved by catalogue priority. Changing a dependency version follows the same review as changing the selected definition.

Avoid general deep inheritance in v1. Prefer composition and explicit overrides. Support for a narrow `extends` feature can be added later if repeated authoring work justifies it; it would need pinned ancestry, depth bounds and explainable merges.

## 7. Fetching and version lifecycle

Resolve a branch/tag to **one exact commit before fetching its manifest and files**. Read all indexed content from that commit. GitHub's contents API accepts commit, branch and tag refs [G1]. Do not fetch the manifest from one branch head and its definitions from a later one.

Validate the index and bounded payloads in staging, check hashes and supported schema/semantics, then publish the cached source revision with an operation receipt. A failed fetch must leave the previous accepted source and every selected printer definition unchanged. Preserve old revisions while referenced by drafts, generated output or restoration snapshots. Bounded garbage collection may remove only unreferenced data.

Record distinct versions for the public format, individual definition, repository commit, runtime/generator and actual local printer plan. A published definition version is immutable: different bytes under the same source/ID/version cause a republish error requiring the author to bump its version. A branch or release label is a discovery aid, not the durable installed identity.

Do not equate a recorded hash with publisher authentication or physical safety. Hashes bind the reviewed bytes; the owner chooses whether to trust that source. The first version can use user-added HTTPS repositories without a central registry or mandatory signing service. Later signing/attestation must distinguish integrity, publisher identity and hardware evidence rather than display one generic “verified” badge.

A repository rename can be reconciled against stable repository identity. A transfer to a new owner or move to a new repository/root must be surfaced and acknowledged before taking further updates; never silently follow a publisher-authored redirect. A deletion, outage or rate limit must not prevent offline generation from the locked local snapshot.

## 8. Configuration, macros and installation trust

Repository content is input, not an installer. The importer must never run setup scripts, Python modules, browser code, package managers, Git hooks/submodules or firmware tools. It must not restart Klipper, resolve private MCU IDs, heat or move anything. Use finite backend operations under Cockpit's existing authority model.

This does **not** imply that definitions are inherently safe just because they are JSON. A declarative heater limit, pin mapping or motor current can still be harmful. Keep application-level invariants, source provenance, compatibility checks and targeted review of consequential changes for built-in and external definitions alike.

For macro composition, prefer supported behaviour records and parameters to application-owned hooks. This permits third-party changes to levelling or tool-change behaviour within defined capabilities without giving every kit ownership of `PRINT_START` or the whole configuration include graph.

**Raw Klipper macros are a distinct advanced capability, not ordinary inert metadata.** Klipper documents template actions and delayed G-code that can execute after startup [K1]. Never evaluate a publisher template on the running printer to produce a preview. JSON validation, text scanning or a source's own test declaration cannot prove arbitrary macros safe.

The initial external-source implementation should accept typed settings and supported behaviour records, while identifying raw-macro packages as unsupported. The wider product still needs an explicit managed custom-macro path: constrained configuration destinations, exact owned sections/macros and include closure, dependency/ownership checks, non-live parsing, a visible code diff and separate activation handling. Implement that path as a supported capability rather than permanently excluding complex upgrades or silently smuggling raw code through `extensions`.

A component requiring an unsupported Klipper fork, Moonraker extension or MCU firmware is displayed with that prerequisite. Source addition does not install it. Firmware/software provisioning belongs to the project's separate workflows.

## 9. Validation, resource bounds and privacy

Apply validation in layers: transport/envelope; trusted schema; reference and capability resolution; semantic composition; generated-output parsing; explicit review and eventual activation. Use the same schema and semantic engine in creator tools and on the printer. Publish structured errors with a definition ID, field path, explanation and remedy. Return all relevant errors in one pass where safe.

The semantic layer covers units and legal values, exact board variants, endpoint/circuit suitability, canonical pin collisions, bus/address sharing, dependency cycles, macro/section ownership, conflicting temperature policies, calibration dependencies and protected output locations. Missing calibration or user installation choices need not prevent catalogue import or draft saving; distinguish that from a malformed definition or unsupported behaviour.

Preserve a boundary between **structurally valid**, **composition supported**, **maintainer-tested** and **commissioned on this printer**. Do not present parser acceptance as confirmation of a safe electrical installation.

Fetch only explicit relative paths under the accepted catalogue root. Reject traversal, absolute/network paths, symlinks, submodules and non-regular files. Because GitHub's contents endpoint can resolve some symlinks, do not rely on that endpoint's returned content alone to establish file type; inspect Git tree modes or equivalent metadata [G1, G3]. Do not automatically retrieve URLs found in guide text, schemas, definitions or external assets. Render labels/descriptions as text or through an explicitly restricted renderer.

Define tested limits for manifest size, individual files, total accepted cache, definition count, dependency depth, parse nesting, requests, timeouts and concurrency. Reject over-budget updates before publication and retain the existing revision. Exact limits are an implementation deliverable based on measured appliance budgets, not an invitation to download an entire vendor repository. Cache manifests and small definition data; do not cache product photographs, guide PDFs or firmware as part of this feature.

Public GitHub browsing must not send the printer's hardware inventory, serial identities or configuration to creators. A future token is stored in the existing protected backend credential facility, never the definition file, URL, browser storage, export or log. Treat raw reference captures and private backups separately from public reusable definitions.

## 10. Compatibility with the current project

The existing contributor recipe already permits new presets of an existing device kind without UI/runtime edits [P2]. Retain that low-cost path. The source loader and public-format adapter should extend the catalogue pipeline, not create a second configuration generator.

The current catalogue schema, internal printer draft schema, catalog validation, generator and persistent store have different responsibilities. Keep private instance state out of the published definition format. Add a source lock/dependency snapshot to the local plan and bind its digest to the existing review/revision checks. Old saved drafts migrate with an explicit mapping to their exact built-in definitions; missing provenance is not filled by selecting the newest similarly named preset.

Catalogue availability can be independent of an individual draft; source selection, pinned dependencies and local overrides must travel with that draft's reproducibility record. Reuse the project's established persistent-storage and capacity mechanisms rather than inventing another unmanaged directory tree.

The current implementation only saves inactive candidates. This proposal adds a catalogue distribution mechanism; it does not turn current Apply into live configuration deployment. Source operations must be testable without serial devices or printer services. The existing end-to-end design brief continues to own future configuration publication and commissioning.

## 11. Delivery sequence and acceptance

**First:** finalise the shared public contract, introduce built-in adapters and creator examples/validator. Exercise one component, one board, one assembly spanning categories and one behaviour composition with positive and negative fixtures. Export/import must preserve meaning and origin.

**Next:** deliver public GitHub source addition, staged validation, unified choices, exact pinning, offline cache, update review and non-destructive disable/remove. This can work with inactive candidate generation; it need not wait for live deployment.

**Then:** broaden the supported behaviour vocabulary and integrate with live publication/commissioning. Add reusable-definition export and private repositories when their value warrants their additional work. Raw macro support receives its own capability and tests. Consider other Git hosts and signed sources later without changing hardware semantics.

No central marketplace, compulsory account, mandatory signing, full Git clone, automatic dependency subscription, generic plugin runtime or multi-provider package solver is required for the first release.

| Acceptance area | Observable result |
| --- | --- |
| Creator independence | An external author publishes a compatible preset without changing sv08-mainline code or obtaining a central approval. |
| Ordinary user path | Add repository once; its bed/toolhead choices appear in the appropriate existing selector without Advanced. |
| Same format | Equivalent built-in and external inputs produce the same resolved output, apart from provenance. |
| No side effects on import | Live configuration, services, MCU connections and heater/motion state remain untouched. |
| Source identity | A repo cannot masquerade as built-in; duplicate names/IDs across sources do not silently overwrite. |
| Unsupported extension | A required unknown capability blocks that definition, with a clear reason; valid unrelated entries remain usable. |
| Consistent snapshot | Branch movement during fetch cannot create a mixed-revision source. Hash/republish failures retain old content. |
| Offline operation | Disconnect network or delete the source; a saved locked plan can still be viewed and regenerated using retained compatible runtime assets. |
| Update control | New catalogue content does not alter selected definitions, dependencies, overrides or live files until the relevant explicit actions. |
| Concurrency | A changed source lock or printer draft invalidates the corresponding old review; loss of acknowledgment requires reconciliation. |
| Dependency resolution | Cross-source impostors, absent prerequisites, cycles and conflicting versions fail deterministically. |
| Calibration and local edits | Preset updates retain explicit overrides for review and invalidate only dependent calibration. |
| Removal | Disabling/removing a source leaves active upgrades and referenced restoration content intact. |
| Import hardening | Duplicate keys, excessive size/depth, traversal, symlinks, script fields and remote schema references cannot trigger execution or unbounded work. |
| Macro handling | Unsupported raw macros are not silently omitted to produce a falsely complete preset; future supported macros get an explicit managed review path. |
| Creator diagnostics | Local validator and printer agree on fixtures; errors identify the exact field and remedy. |
| Public export | Reusable definitions contain no machine-specific identity, secrets or calibration copied as universal defaults. |

Use automated schema/fixture tests for routine data changes. Concentrate deeper engineering review on new behaviour capabilities, electrical mappings, raw macro execution and live publication. A third-party source is not a reason to burden every normal selection with a new manual approval process.

## 12. Decisions to carry forward

Adopt the common format, user-added GitHub sources, separate source management, exact version pinning, explicit updates and preservation of local overrides now as design requirements. These are foundational to the page, not a distant optional marketplace feature.

Final schema key names, the smallest useful behaviour vocabulary, stable publication URLs and tested cache limits remain implementation choices. Before freezing the format, trial it with the requested bed/Eddy combination and a representative multi-component toolhead or filament upgrade. Use real guide-derived definitions for that trial; the abbreviated example above is not a hardware test fixture.

## References

All external documentation below was checked on 6 October 2026. Repository references use the inspected commit. External documentation informs the proposed design; it does not demonstrate that a source loader or stable public schema already exists in sv08-mainline.

- **[P1]** [Current catalogue schema](https://github.com/drew442/sv08-mainline/blob/11912e05c7a14650cc7a0c486e40482da9241760/catalog/printer/catalog.schema.json): Draft 2020-12, current catalogue fields and supported kinds.
- **[P2]** [Current catalogue and contributor recipe](https://github.com/drew442/sv08-mainline/blob/11912e05c7a14650cc7a0c486e40482da9241760/docs/development/printer-hardware-catalog.md): current data-only preset path, provenance, semantic checks and inactive output.
- **[S1]** [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12): proposed public validation dialect.
- **[S2]** [JSON Schema object validation](https://json-schema.org/understanding-json-schema/reference/object): composition and property-closure behaviour.
- **[S3]** [Dialect and vocabulary declaration](https://json-schema.org/understanding-json-schema/reference/schema): distinction between dialect declarations and application policy.
- **[G1]** [GitHub repository contents API](https://docs.github.com/en/rest/repos/contents): public reads, commit refs and symlink handling.
- **[G2]** [GitHub REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api): need for bounded, cached fetches.
- **[G3]** [GitHub Git trees API](https://docs.github.com/en/rest/git/trees): tree entries and file modes.
- **[K1]** [Klipper command templates](https://www.klipper3d.org/Command_Templates.html): actions, evaluation and startup-capable delayed G-code.
