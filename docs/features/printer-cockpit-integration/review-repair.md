# Independent review and bounded repairs

2026-10-04. Original candidate `9476304` failed independent Sol6.1/high review.
The failure is retained in Git history at `78b4c67` and in private source-bound
reproductions. It is not installed acceptance.

- F1: a raw concurrent writer after validation could have its content overwritten
  during restoration. Repair requires shared exclusion for supported staging,
  restoration and host-refresh entrypoints, from validation through completion.
- F2: keeping local selections during unsupported saved catalog/schema handling
  cleared the local draft. Repair must preserve the draft for export and require
  explicit discard, while unsupported saved state continues to block mutations.
- F3: storage receipts omitted peak temporary/report/backup inode accounting and
  comparisons with accepted factory-capacity reserves.

## Original approver clarification

The independent original approver, in its same full-role Sol6.1/medium session,
confirmed that supported operations on coordinator-exclusive offline roots are
within the original approval. No approval amendment or owner requirement change
is needed. Advisory exclusion must cover all supported entrypoints, and both
fresh and historical roots must demonstrate contention refusal without mutation.
Preexisting bytes/metadata/inventory drift must refuse before any restoration;
newly detected drift must be retained and reported. Preserve interruption and
host-only refresh checks. Root-inode replacement and arbitrary noncooperating
writers are forbidden by the exclusive-root operating contract; a lock cannot
provide multi-file atomicity against them. This limitation is explicit, not a
claim that the original failing reproduction passed or that review is waived.

Private clarification: `local/feature-workflow/probes/printer-integration-20261004/constraint-clarification/`.
Effective role/model/effort were coordinator-verified. This interpretation does
not accept the repair or grant printer authority. Fresh independent delivery
review must establish the repaired behavior and all original acceptance checks.
