#!/usr/bin/env python3
"""Isolated expiry regression test; does not touch the production database."""

import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch


class FakeScan:
    def __init__(self, events):
        self.stdout = io.StringIO("".join(json.dumps(event) + "\n" for event in events))

    def wait(self):
        return 0


def main():
    path = Path(__file__).resolve().parent.parent / "bin" / "strfry-prune-events"
    loader = importlib.machinery.SourceFileLoader("strfry_prune_events", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)

    now = 2_000_000
    events = [
        {"id": "old_last", "kind": 1059, "created_at": now - 172801, "tags": []},
        {"id": "ephemeral", "kind": 20001, "created_at": now - 91, "tags": []},
        {"id": "nip40", "kind": 1, "created_at": now, "tags": [["expiration", str(now - 1)]]},
        {"id": "live", "kind": 1401, "created_at": now, "tags": []},
    ]
    calls = []

    def record(command, **kwargs):
        calls.append(command)
        return None

    with patch.object(module.subprocess, "run", side_effect=record), \
         patch.object(module.subprocess, "Popen", return_value=FakeScan(events)), \
         patch.object(module.time, "time", return_value=now), \
         patch.object(module.sys, "argv", ["strfry-prune-events", "--binary", "/fake/strfry"]):
        assert module.main() == 0

    assert calls[0][-3:] == ["delete", "--age", "172800"]
    removed = set()
    for command in calls[1:]:
        removed.update(json.loads(command[-1])["ids"])
    assert removed == {"old_last", "ephemeral", "nip40"}, removed
    print("PASS: last old event, ephemeral and NIP-40 removed; live event preserved")


if __name__ == "__main__":
    main()
