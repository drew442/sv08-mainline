"""Narrow build helpers for pinned Monocypher Ed25519 guest verification."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
MONOCYPHER = REPO / 'upstream/monocypher'
MONOCYPHER_COMMIT = 'ab2b16dd619ad5f6979a4fbe69cfa324a6fcc35f'
ED25519_SOURCES = (
    MONOCYPHER / 'src/monocypher.c',
    MONOCYPHER / 'src/optional/monocypher-ed25519.c',
)
ED25519_INPUTS = (*ED25519_SOURCES,
                  MONOCYPHER / 'src/monocypher.h',
                  MONOCYPHER / 'src/optional/monocypher-ed25519.h',
                  MONOCYPHER / 'LICENCE.md')
SPKI_ED25519_PREFIX = bytes.fromhex('302a300506032b6570032100')


def raw_public_key(pem: bytes) -> bytes:
    """Extract a strictly encoded 32-byte Ed25519 key via OpenSSL's PEM parser."""
    with tempfile.TemporaryDirectory(prefix='sv08-ed25519-key-') as temporary:
        source = Path(temporary) / 'key.pem'
        source.write_bytes(pem)
        result = subprocess.run(['openssl', 'pkey', '-pubin', '-in', str(source),
                                 '-outform', 'DER'], check=True, capture_output=True,
                                 timeout=10)
    der = result.stdout
    if len(der) != len(SPKI_ED25519_PREFIX) + 32 or not der.startswith(SPKI_ED25519_PREFIX):
        raise ValueError('Expected one Ed25519 SubjectPublicKeyInfo key')
    return der[len(SPKI_ED25519_PREFIX):]


def source_hashes() -> dict[str, str]:
    return {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in ED25519_INPUTS}
