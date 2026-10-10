# Pinned RAUC signer trust exception

`0001-per-request-signer-trust.patch` applies to pristine RAUC v1.15.2,
commit `4fb7c798d6ae412344fb8f8d310d773046af3441`. The source archive identity
remains in `configs/host-os/rauc-package.json`; the package version is
`1.15.2-0sv08.2`. `scripts/package_rauc.py` verifies both archive and patch SHA256,
applies with `patch --batch --fuzz=0 -p1`, and records patch/config/toolchain and
binary/package hashes. Retire this patch when upstream provides this interface.

The [owner request](../../docs/features/automatic-update-policy/owner-request.md)
authorizes a manual, reviewed per-update provenance exception. Strict automatic
and default manual checks remain unchanged. This patch supplies no global service
configuration or persistent trust change.

Interfaces:

* `rauc info --ignore-signer-trust --output-format=json-2 BUNDLE`
* `rauc install --ignore-signer-trust --require-manifest-hash=HASH BUNDLE`
* D-Bus `InstallBundle` option `ignore-signer-trust` is a boolean, default false.

`info` JSON-2 reports the upstream top-level `manifest-hash`; pass this exact
SHA256 to upstream `--require-manifest-hash` on installation. Compatibility remains
an independent upstream `--ignore-compatible` option. The application controls
which reviewed manual request can set these options.

The exception only sets OpenSSL `CMS_NO_SIGNER_CERT_VERIFY`: CMS parsing, signed
attributes and mathematical signature verification remain enabled. The inline
signed manifest is verified before loading; verity and image checks remain enabled.
No `verification_disabled`, `CMS_NO_CONTENT_VERIFY`, `CMS_NO_ATTR_VERIFY`,
`CHECK_BUNDLE_NO_VERIFY`, or `--no-verify` substitutes for this exception. Combining
`info --no-verify` with the exception is rejected. Detached/plain bundles are
rejected with the exception; supported inline formats are verity and crypt.

A waived chain is not presented as trusted: readable info identifies signature
verification without signer trust, and `RAUC_BUNDLE_SPKI_HASHES` is empty for install
hooks when no verified chain exists. Certificate CN policy remains enforced;
certificate chain validity and signing-time chain evaluation are waived.

`tests/rauc_provenance.py` creates tiny disposable test bundles and exercises actual
native RAUC info/install with a private D-Bus and regular-file slots in a private
mount namespace. It requires explicit execution and root for loop/verity mounts.
It establishes offline installer evidence, not a physical printer or release claim.

Focused validation:

```sh
python3 -m unittest discover -s tests -p test_package_rauc.py
sudo unshare --mount --propagation private python3 tests/rauc_provenance.py \
  --rauc /path/to/patched/native/rauc --work /new/disposable/path --execute
```

The fixture checks trusted/default and unknown/default info, explicit unknown-signer
info and installation, wrong manifest binding, malformed/missing CMS, damaged
mathematical signature, damaged verity payload, refusal of a `--no-verify`
combination, empty hook SPKI metadata, paired readback, preserved active/primary,
and a subsequent strict install rejection. RAUC `info` only verifies the external
manifest for verity containers; successful `info` alone is not payload evidence.
