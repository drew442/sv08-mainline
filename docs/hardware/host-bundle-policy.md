# Signed update compatibility admission

2026-09-10. Read-only implementation and signed offline fixture tested; not an
installed update coordinator or deployable release.

[The admission module](../../runtime/sv08_bundle.py) asks RAUC to authenticate a
locally staged bundle with the configured keyring, then checks its signed hardware
compatible string and project metadata. The accepted metadata is exactly:

```ini
[meta.sv08]
layout=ab-8gb-v1
state-schema=1
klipper-commit=f0892d82b0f1c1228454f09eb508eddde2250f4b
```

The policy also requires a verity bundle, a valid release identifier, exactly one
192 MiB boot image and one 2048 MiB root image, complete SHA-256 digests, and a
bundle within 1 GiB. It rejects image variants, artifacts, non-raw image payloads,
adaptive updates, custom handlers and hooks until explicitly supported. State
schema 1 is the only implemented migration. A changed Klipper revision requires
a separately tested host/MCU compatibility or coordinated MCU-update policy;
this mechanism never flashes an MCU.

Use RAUC's supported `meta.*` manifest sections rather than changing its source.
Primary source inspected locally on 2026-09-10: RAUC commit
`4fb7c798d6ae412344fb8f8d310d773046af3441`, `docs/reference.rst`
(`meta.<label>` sections) and `src/manifest.c` (`r_manifest_to_dict`). This is
project policy for a gap RAUC deliberately leaves to integrators. Retire the
custom validator if upstream supplies equivalent declarative constraints; see
[decision 0006](../decisions/0006-host-state-integration.md).

## Offline test

A new fixture uses the original paired capacity images plus the metadata above,
signed with the same ignored test-only key. Its compatible string remains
`sv08-offline-test-only`. No private key or generated bundle is committed.

```sh
python3 runtime/sv08_bundle.py build/rauc-bundle-metadata-v1/paired.raucb \
  --rauc build/rauc-native-v2/rauc \
  --keyring build/rauc-bundle-v1/keys/test.cert \
  --policy build/rauc-bundle-metadata-v1/policy.json
```

The authenticated fixture passes. The original correctly signed bundle without
metadata is rejected. The new correctly signed bundle is also rejected against
policies with a different compatible string, layout, state schema or Klipper pin.
Unit tests additionally cover malformed dimensions/digests, extra images,
unsupported payload behavior and staging-budget limits. Results and the signed
bundle hash are in [the evidence record](host-bundle-policy-20260910.json).

`rauc info` authenticates the inline manifest; it does not read and verify every
payload block. The result explicitly reports `full_payload_verified=false`.
The installer must retain RAUC verity verification. The SHA-256 recorded here is
for identifying the exact staged file, not an additional trust root. The file is
checked for changes during inspection; a future installer must own/lock its
staging directory and revalidate the exact file before using it.

The release builder still must cross-check metadata against the root's actual
release manifest and packaged Klipper provenance, paired kernel/initramfs/DTB,
and reviewed hardware profile. The signing process must not bless declarations
that have not been checked. This test uses dummy boot content and does not prove
that relationship. No production policy/keyring is installed yet. Installation,
next-boot selection, idle admission, interrupted-transaction reconciliation and
health confirmation remain on the [completion checklist](host-os-tasks.md).
