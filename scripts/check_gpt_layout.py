#!/usr/bin/env python3
"""Read-only GPT/SPL/environment collision audit for regular-file image candidates.

The shared runtime parser also supports explicit read-only block-device audits;
this command-line wrapper intentionally accepts regular image files only.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_gpt import inspect


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('--environment-layout', type=Path)
    a = p.parse_args()
    regions = []
    if a.environment_layout:
        layout = json.loads(a.environment_layout.read_text())
        if layout['format_version'] != 1 or len(layout['copy_offsets_bytes']) != 2:
            raise ValueError('Expected the reviewed two-copy environment layout')
        regions = [(offset, layout['size_bytes']) for offset in layout['copy_offsets_bytes']]
    print(json.dumps(inspect(a.image, environment_regions=regions), indent=2))


if __name__ == '__main__':
    main()
