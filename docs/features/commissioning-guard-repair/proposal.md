# Commissioning dependency-source repair

Reproduce the three PR29 commissioning errors, reconcile fixture/implementation provenance against the actual supported staging contract, and repair the demonstrated defect. Preserve exact dependency matching and refusal of incompatible or modified sources.

Acceptance: commissioning suite passes with only the existing explicit selected-tool opt-in skip; regression coverage proves incompatible dependency sources remain refused; relevant adjacent staging and boot-health checks pass. Publish source-bound evidence and a review PR. Offline fixtures only; no hardware qualification.
