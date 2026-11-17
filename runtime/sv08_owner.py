"""Private persistent owner enrollment and a slot-local, ephemeral PAM shadow.

Only recovery enrollment writes the persistent record. Public images retain a
locked account; boot never creates or repairs an enrollment. Password rotation is
an explicit local recovery operation, not a write to the ephemeral shadow.
"""
import json
import os
from pathlib import Path
import re
import stat
import uuid

from sv08_export import opened, identity, publish
from sv08_web import password_hash

RECORD = 'owner.json'
HASH = r'\$6\$[A-Za-z0-9./]{1,16}\$[A-Za-z0-9./]{86}'


def require(condition, message):
    if not condition: raise ValueError(message)


def validate_password(password, confirmation):
    require(type(password) is str and 12 <= len(password) <= 256 and
            all(32 <= ord(c) <= 126 for c in password),
            'Use 12–256 printable ASCII characters, including spaces if desired.')
    require(password == confirmation, 'The passwords do not match.')


class Owner:
    def __init__(self, root, root_uid=0):
        self.root, self.root_uid = Path(root), root_uid

    def directory(self):
        # opened walks every component without following symlinks. Callers hold
        # the recovery media lease for writes; root/system must be privileged.
        for path in (self.root, self.root/'system'):
            with opened(path) as fd:
                info = os.fstat(fd)
                require(info.st_uid == self.root_uid and not stat.S_IMODE(info.st_mode) & 0o022,
                        'Owner storage must be privileged and not writable by other users.')
        return opened(self.root/'system')

    def load(self):
        with self.directory() as directory:
            try: fd = os.open(RECORD, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except FileNotFoundError: return None, None
            try:
                info = os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == self.root_uid and
                        stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= 2048,
                        'Invalid private owner enrollment; no repair was attempted.')
                try: value = json.loads(os.read(fd, 2049))
                except (ValueError, UnicodeError): raise ValueError('Invalid private owner enrollment; no repair was attempted.') from None
                require(identity(os.fstat(fd)) == identity(info), 'Owner enrollment changed while reading.')
            finally: os.close(fd)
        require(type(value) is dict and set(value) == {'format_version','username','uid','enrollment','password_hash'} and
                type(value['format_version']) is int and value['format_version'] == 1 and value['username'] == 'sv08' and
                type(value['uid']) is int and value['uid'] == 1000 and type(value['enrollment']) is str and
                re.fullmatch('[0-9a-f]{32}', value['enrollment']) and type(value['password_hash']) is str and
                re.fullmatch(HASH, value['password_hash']), 'Invalid private owner enrollment; no repair was attempted.')
        return value, list(identity(info))

    def status(self):
        value, stamp = self.load()
        return dict(enrolled=value is not None, enrollment=value['enrollment'] if value else None, stamp=stamp)

    def save(self, password, confirmation, expected, reset=False, recheck=lambda: None):
        validate_password(password, confirmation)
        require(type(reset) is bool, 'Choose enrollment or explicit password reset.')
        require(self.status() == expected, 'Owner enrollment changed; review again.')
        require(expected['enrolled'] == reset,
                'An enrolled owner requires explicit password reset.' if expected['enrolled'] else 'No owner is enrolled; choose initial setup.')
        value = dict(format_version=1, username='sv08', uid=1000, enrollment=uuid.uuid4().hex,
                     password_hash=password_hash(password))
        temporary = '.owner-'+uuid.uuid4().hex
        with self.directory() as directory:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            try:
                with os.fdopen(fd, 'w') as stream:
                    json.dump(value, stream, sort_keys=True); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
                require(self.status() == expected, 'Owner enrollment changed; review again.')
                recheck()
                if reset: os.replace(temporary, RECORD, src_dir_fd=directory, dst_dir_fd=directory)
                else: publish(directory, temporary, RECORD)
                os.fsync(directory)
            finally:
                try: os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError: pass


def shadow_text(shadow, passwd, owner_hash):
    users = [line.split(':') for line in passwd.splitlines() if line.split(':')[0] == 'sv08']
    require(len(users) == 1 and len(users[0]) == 7 and users[0][2:4] == ['1000','1000'],
            'The slot must contain the fixed sv08 UID/GID 1000 account.')
    lines = shadow.splitlines(keepends=True)
    found = 0
    for index, line in enumerate(lines):
        fields = line.rstrip('\n').split(':')
        require(len(fields) == 9 and fields[0], 'Invalid slot shadow.')
        if fields[0] != 'sv08': continue
        found += 1
        # No owner means locked regardless of the slot's original contents.
        fields[1] = owner_hash if owner_hash is not None else '*'
        lines[index] = ':'.join(fields)+ ('\n' if line.endswith('\n') else '')
    require(found == 1, 'The slot must contain exactly one sv08 shadow entry.')
    return ''.join(lines)


def prepare_shadow(root, data, root_uid=0):
    root = Path(root)
    owner, _ = Owner(data, root_uid).load()
    def slot_text(name):
        with opened(root/'etc'/name, flags=os.O_RDONLY | os.O_NOFOLLOW) as fd:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_size <= 1024*1024,
                    'Invalid slot account file.')
            return os.read(fd, 1024*1024+1).decode()
    raw = shadow_text(slot_text('shadow'), slot_text('passwd'), owner['password_hash'] if owner else None)
    directory = root/'run/sv08'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with opened(directory) as parent:
        info = os.fstat(parent)
        require(info.st_uid == root_uid and not stat.S_IMODE(info.st_mode) & 0o022, 'Invalid ephemeral owner storage.')
        fd = os.open('owner-shadow', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'w') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return directory/'owner-shadow'
