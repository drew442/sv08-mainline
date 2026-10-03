# Independent software review: F1

Outcome: failed at candidate `08097f2e5b065325d0e4ef68b358c00ba1e3719f`.
Reviewer: separate feature_verifier_high, effective GPT-6.1 Sol/high, full-access
with approvals never. Native thread capacity was unavailable; the documented
separate full-role CLI fallback was used. Runtime receipt and unchanged formal
result are preserved beside this summary.

The helper requires `sv08_gpt.inspect()` to return `disk_guid`. Its exact historical
installed dependency validates GUID agreement but does not return that field.
The current repository version does. The otherwise admissible health path therefore
raises KeyError before confirmation, retains a failed record and refuses same-boot
retry. No write occurs. Passing mock and import-only tests did not expose this API
mismatch; passing source-preimage checks do not prove callable compatibility.

The reviewer reproduced the failure with the exact staged historical closure and
a valid disposable 32 MiB six-partition GPT, then reproduced zero writes, durable
failure and retry refusal. Two bounded auxiliary probes were used; no hardware or
production source was changed. Preserve GUID verification, both CRC/array checks
and exact closure while correcting the caller and exercising the real historical
inspector through positive A1/A2/A3 and wrong-GUID paths.

The full 25-file recorded-base diff and 234 hash/scope/provenance/path checks were
reviewed. Fifteen focused tests passed with one selected-tool opt-in skip; retained
18-case tool proof and offline theme evidence were supported. The historical API
defect blocks baseline and overlay acceptance. Installed boots/access/sensors and
exact-operation review remain pending. Original requirements, all six constraints,
owner password amendment and H12 scope remain unchanged.

Raw reviewer scripts, source-bound reproductions, full findings and original logs
remain private. This summary does not substitute for the formal failed result.
