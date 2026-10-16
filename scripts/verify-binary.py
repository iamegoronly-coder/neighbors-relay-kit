#!/usr/bin/env python3
"""Check a local Linux x86_64 binary against an independently obtained SHA-256.
This is an integrity check, not a claim about the safety or origin of the program.
The file is read, never executed.
"""
import argparse
import hashlib
from pathlib import Path
import re
import sys


def verify(path, expected):
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("expected SHA-256 must be 64 lowercase hexadecimal characters")
    with path.open("rb") as stream:
        header = stream.read(64)
        if (len(header) != 64 or header[:7] != b"\x7fELF\x02\x01\x01"
                or int.from_bytes(header[16:18], "little") not in (2, 3)
                or int.from_bytes(header[18:20], "little") != 62):
            raise ValueError("not a Linux-compatible ELF64 x86_64 executable")
        stream.seek(0)
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected:
        raise ValueError(f"SHA-256 mismatch: expected {expected}, got {digest}")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        print("Verified SHA-256:", verify(args.binary, args.sha256))
    except (ValueError, OSError) as error:
        print(f"verify-binary: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
