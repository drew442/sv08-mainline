#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mandatory read-only public matching PROJECT source qualification.

A passing result is project-source-only, never image/hardware/redistribution readiness.
--public-source supplies exact HTTPS archive and patch/build/install input pins.
Every input must be a verified archive member or independently downloaded bytes.
No caller availability/completeness assertions are accepted. No root is mutated.
"""
import argparse
import io
import ipaddress
from http.client import HTTPSConnection
import json
from pathlib import PurePosixPath
import re
import tarfile
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler, HTTPSHandler, Request
from project_license import digest, validate

HASH = re.compile(r'[0-9a-f]{64}')
REVISION = re.compile(r'[0-9a-f]{40}')
MAX_ARCHIVE = 32*1024*1024
MAX_EXPANDED = 64*1024*1024


def immutable_url(url, revision, sha):
    if not isinstance(url, str): raise ValueError('Missing public source URL')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Anonymous immutable HTTPS URL required')
    try: address = ipaddress.ip_address(parsed.hostname)
    except ValueError: address = None
    if address is not None and not address.is_global: raise ValueError('Public source must use a public host')
    if parsed.hostname.lower() in ('localhost',) or parsed.hostname.lower().endswith(('.localhost','.local','.internal')):
        raise ValueError('Public source must use a public host')
    if any(part.lower() in ('token','auth','credentials','private') for part in parsed.path.split('/')):
        raise ValueError('Credential/private source URL refused')
    tokens = re.split(r'[^a-zA-Z0-9]', parsed.path)
    if revision not in tokens and sha not in tokens: raise ValueError('Moving or unpinned public source URL')
    return url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Public source redirects are not qualified; use the final immutable URL')


class PublicConnection(HTTPSConnection):
    def connect(self):
        super().connect()
        if not ipaddress.ip_address(self.sock.getpeername()[0]).is_global:
            self.close()
            raise ValueError('Public source endpoint resolved to a private address')


class PublicHTTPS(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(PublicConnection, req, context=self._context)


def download(url):
    # No environment proxy credentials, cookies or authenticated connector transport.
    opener = build_opener(ProxyHandler({}), NoRedirect(), PublicHTTPS())
    with opener.open(Request(url, headers={'User-Agent':'SV08-public-source-check/1'}), timeout=30) as response:
        if response.status != 200: raise ValueError('Public source unavailable')
        raw = response.read(MAX_ARCHIVE+1)
    if len(raw) > MAX_ARCHIVE: raise ValueError('Public source download exceeds bound')
    return raw


def archive_files(raw):
    result = {}; total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
            for entry in archive:
                path = PurePosixPath(entry.name)
                if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe source archive path')
                if entry.isdir(): continue
                if not entry.isfile(): raise ValueError('Source archive contains nonregular member')
                if entry.size > 8*1024*1024: raise ValueError('Source archive member exceeds bound')
                total += entry.size
                if total > MAX_EXPANDED or len(result) >= 10000: raise ValueError('Source archive expansion exceeds bound')
                if entry.name in result: raise ValueError('Duplicate source archive member')
                result[entry.name] = digest(archive.extractfile(entry).read())
    except tarfile.TarError as error:
        raise ValueError('Invalid public source archive') from error
    return result


def required_inputs(sources):
    return dict(patches={n for n in sources if n.startswith('patches/')},
                build_inputs={n for n in sources if n.startswith(('scripts/','configs/')) or n in ('upstream-lock.json','.gitmodules')},
                install_inputs={n for n in sources if n.startswith('docs/development/') or
                    (n.startswith('scripts/') and any(word in PurePosixPath(n).name for word in ('install','stage','integrate','prepare')))})


def verify_public(record, manifest, transport=None):
    """Transport injection is for tests; the CLI always performs real anonymous HTTP."""
    fetch = transport or download
    if isinstance(manifest, (str, bytes)) or hasattr(manifest, '__fspath__'):
        with open(manifest) as stream: manifest = json.load(stream)
    revision = record.get('source_revision')
    if record.get('development') is not False or not REVISION.fullmatch(revision or ''):
        raise ValueError('Dirty or unidentified development source cannot qualify')
    if not record.get('release'): raise ValueError('Missing installed release provenance')
    declared = record['release']['identity'].get('project_source_revision')
    if declared is not None and declared != revision: raise ValueError('Installed release source revision mismatch')
    if set(manifest) != {'format_version','source_revision','archive','archive_prefix','patches','build_inputs','install_inputs'} or manifest.get('format_version') != 1:
        raise ValueError('Exact public source manifest schema required')
    if manifest['source_revision'] != revision: raise ValueError('Public source revision mismatch')
    pin = manifest['archive']
    if set(pin) != {'url','sha256'} or not HASH.fullmatch(pin.get('sha256','')): raise ValueError('Invalid source archive pin')
    url = immutable_url(pin['url'], revision, pin['sha256'])
    raw = fetch(url)
    if not isinstance(raw, bytes) or digest(raw) != pin['sha256']: raise ValueError('Public source archive hash mismatch')
    members = archive_files(raw)
    prefix = manifest['archive_prefix']
    if not isinstance(prefix,str) or (prefix and (not prefix.endswith('/') or PurePosixPath(prefix).is_absolute() or '..' in PurePosixPath(prefix).parts)):
        raise ValueError('Invalid source archive prefix')
    sources = record['source_files']
    for name, sha in sources.items():
        if members.get(prefix+name) != sha: raise ValueError('Public corresponding source mismatch: '+name)
    coverage = required_inputs(sources)
    verified = {}
    for group, required in coverage.items():
        pins = manifest[group]
        if not isinstance(pins,list): raise ValueError('Explicit public input coverage required')
        names = set(); verified[group] = []
        for item in pins:
            name = item.get('path'); sha = item.get('sha256')
            if name in names or name not in required or sha != sources[name]: raise ValueError('Public input pin mismatch')
            names.add(name)
            if set(item) == {'path','sha256','archive_member'} and item['archive_member'] is True:
                if members.get(prefix+name) != sha: raise ValueError('Missing public archive input')
            elif set(item) == {'path','sha256','url'}:
                input_url = immutable_url(item['url'], revision, sha)
                if digest(fetch(input_url)) != sha: raise ValueError('Public patch/build/install input hash mismatch')
            else: raise ValueError('Verified archive member or anonymous pinned URL required')
            verified[group].append(item)
        if names != required: raise ValueError('Missing public '+group+' coverage')
    return dict(qualified=True, scope='project-source-only', overall_release_qualified=False,
                source_revision=revision, build_id=record['build_id'], archive=pin,
                inputs=verified, verification='anonymous HTTPS bytes and exact corresponding-source hashes')


def qualify(root, manifest):
    record = validate(root)
    result = verify_public(record, manifest)
    # Recheck root after transport: late release/file drift must not qualify.
    if validate(root) != record: raise ValueError('Project root changed during public verification')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--public-source', required=True)
    args = parser.parse_args()
    try: print(json.dumps(qualify(args.root,args.public_source),sort_keys=True,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as error: parser.exit(1, 'Project source qualification refused: '+str(error)+'\n')


if __name__ == '__main__': main()
