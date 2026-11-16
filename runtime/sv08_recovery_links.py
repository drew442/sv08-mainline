"""Narrow provisioned link and journal-mode compatibility for recovery records.

Targets are literal strings, never paths to open. Identity generations are
separately required to be real directories via the caller's safe inventory.
"""
import os
import re
import stat

README_TARGET = '../../usr/share/doc/systemd/README.logs'


def validate_modes(entries, format_version=2):
    """Preserve only the anchored systemd journal directory's special mode.

    Version 2 binds this metadata to archive nodes. Legacy archives retain their
    original ordinary-permission bound; no special regular-file bits are allowed.
    """
    for relative, metadata in entries.items():
        mode = metadata['mode']
        if type(mode) is int and 0 <= mode <= 0o777: continue
        prefix = None
        if relative[-3:] == ('shared', 'logs', 'journal'):
            prefix = relative[:-3]
        elif (len(relative) >= 4 and relative[-4:-1] == ('shared', 'logs', 'journal') and
                re.fullmatch('[0-9a-f]{32}', relative[-1])):
            prefix = relative[:-4]
        if (format_version != 2 or mode != 0o2755 or metadata['type'] != 'directory' or
                metadata['uid'] != 0 or prefix is None or
                entries.get((*prefix, 'state.json'), {}).get('type') != 'file' or
                any(entries.get(relative[:n], {}).get('type') != 'directory'
                    for n in range(1, len(relative)))):
            raise ValueError('Unsafe recovery permission metadata')


def link_target(relative, target, prefix=()):
    relative = tuple(relative)
    if relative == (*prefix, 'shared', 'logs', 'README') and target == README_TARGET:
        return None
    if (relative in ((*prefix, 'system', 'identity', 'current'),
                     (*prefix, 'system', 'identity', 'previous')) and
            type(target) is str and re.fullmatch(r'generations/[0-9a-f]{32}', target)):
        return (*prefix, 'system', 'identity', 'generations', target.split('/')[1])
    raise ValueError('Unsupported recovery link target or path')


def read_link(directory, name, stamp, identity):
    before = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if identity(before) != stamp or not stat.S_ISLNK(before.st_mode):
        raise ValueError('Recovery link changed while reading')
    target = os.readlink(name, dir_fd=directory)
    if identity(os.stat(name, dir_fd=directory, follow_symlinks=False)) != stamp:
        raise ValueError('Recovery link changed while reading')
    return target


def validate_links(entries):
    """Bind each link to real state ancestry and a regular, possibly damaged registry.

    This includes retained and configured state roots and a state root itself.
    Entries map relative tuples to directory/file/symlink kind and target.
    """
    for relative, (kind, target) in entries.items():
        if kind != 'symlink': continue
        prefix = relative[:-3]
        if (len(relative) < 3 or entries.get((*prefix, 'state.json'), (None, None))[0] != 'file' or
                any(entries.get(prefix[:n], (None, None))[0] != 'directory' for n in range(1, len(prefix)+1))):
            raise ValueError('Recovery link requires a real state directory and regular registry')
        generation = link_target(relative, target, prefix)
        if generation is not None:
            for n in range(1, len(generation)+1):
                if entries.get(generation[:n], (None, None))[0] != 'directory':
                    raise ValueError('Recovery identity selector requires a real generation directory')
