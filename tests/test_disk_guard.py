#!/usr/bin/env python3
"""Disk guard thresholds on a temporary directory with a fake systemctl; no services touched."""
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
GUARD = KIT / "bin" / "strfry-disk-guard"
FAKE = Path(__file__).resolve().parent / "fake-systemctl.sh"


def run(action, database, **limits):
    args = [sys.executable, str(GUARD), action, "--database-dir", str(database),
            "--systemctl-bin", str(FAKE)]
    for name, value in limits.items():
        args += [f"--{name.replace('_', '-')}", str(value)]
    return subprocess.run(args, capture_output=True, text=True).returncode


with tempfile.TemporaryDirectory() as temp:
    database = Path(temp)
    (database / "data.mdb").write_bytes(b"x" * 4096)
    roomy = dict(max_bytes=1 << 20, min_free_bytes=1)
    assert run("check", database, **roomy) == 0
    assert run("enforce", database, **roomy) == 0
    assert run("check", database, max_bytes=4096, min_free_bytes=1) == 1
    assert run("enforce", database, max_bytes=4096, min_free_bytes=1) == 1
    assert run("check", database, max_bytes=1 << 20, min_free_bytes=1 << 62) == 1
print("PASS disk guard: within limits, database budget and free-space reserve")
