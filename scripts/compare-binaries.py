#!/usr/bin/env python3
"""Compare two local files without executing either. Exit 0 equal, 1 different, 2 error."""
import argparse
import filecmp
import hashlib
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("built", type=Path)
    parser.add_argument("published", type=Path)
    args = parser.parse_args()
    try:
        for path in (args.built, args.published):
            with path.open("rb") as stream:
                print(hashlib.file_digest(stream, "sha256").hexdigest(), path)
        equal = filecmp.cmp(args.built, args.published, shallow=False)
    except OSError as error:
        print(f"compare-binaries: {error}", file=sys.stderr)
        return 2
    print("IDENTICAL: every byte matches" if equal else "DIFFERENT: do not claim equivalence")
    return 0 if equal else 1


if __name__ == "__main__":
    sys.exit(main())
