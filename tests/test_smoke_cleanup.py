#!/usr/bin/env python3
"""No database or network: exact run ownership, malformed manifests and lost ACKs."""
import asyncio
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from smoke_manifest import SmokeManifest

KIT = Path(__file__).resolve().parent.parent
RELAY = "wss://relay.example.org/relay"


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


cleanup = load("cleanup", KIT / "scripts/cleanup-smoke-events")


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "run.jsonl"
        self.own = {"id": "a" * 64, "pubkey": "b" * 64}
        self.other = "c" * 64
        self.journal = SmokeManifest(self.path, RELAY)
        self.journal.record(self.own)
        self.journal.close()

    def invoke(self, execute=True, relay=RELAY):
        calls = []
        argv = ["cleanup", "--manifest", str(self.path), "--relay", relay]
        if execute:
            argv.append("--execute")
        with patch.object(sys, "argv", argv), patch.object(cleanup.subprocess, "run", side_effect=lambda cmd, **kw: calls.append(cmd)), \
             patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO):
            result = cleanup.main()
        return result, calls

    def test_only_this_runs_ids_deleted_even_when_other_record_has_same_prefix(self):
        # Both records could have content 'relay-smoke-...'; only one was in our run.
        database = {self.own["id"], self.other}
        result, calls = self.invoke()
        self.assertEqual(result, 0)
        for command in calls:
            self.assertEqual(command[-3:-1], ["delete", "--filter"])
            database.difference_update(json.loads(command[-1])["ids"])
        self.assertEqual(database, {self.other})

    def test_dry_run_never_invokes_strfry(self):
        self.assertEqual(self.invoke(execute=False), (0, []))

    def test_wrong_relay_never_deletes(self):
        self.assertEqual(self.invoke(relay="wss://other.example/relay"), (1, []))

    def test_truncated_manifest_rejects_all_deletion(self):
        with self.path.open("a") as stream:
            stream.write('{"id":')
        self.assertEqual(self.invoke(), (1, []))

    def test_short_id_cannot_become_a_nostr_prefix_filter(self):
        with self.path.open("a") as stream:
            stream.write(json.dumps({"id": "abcd", "pubkey": "b" * 64}) + "\n")
        self.assertEqual(self.invoke(), (1, []))

    def test_empty_run_never_invokes_strfry(self):
        self.path.write_text(self.path.read_text().splitlines()[0] + "\n")
        self.assertEqual(self.invoke(), (0, []))

    def test_existing_manifest_is_not_overwritten(self):
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            SmokeManifest(self.path, RELAY)
        self.assertEqual(before, self.path.read_bytes())

    def test_private_file_and_duplicate_event(self):
        path = self.path.parent / "second.jsonl"
        journal = SmokeManifest(path, RELAY)
        journal.record(self.own)
        journal.record(self.own)
        journal.close()
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(cleanup.read_manifest(path, RELAY), [self.own["id"]])

    def test_batches_are_exact_and_bounded(self):
        with self.path.open("a") as stream:
            for i in range(205):
                stream.write(json.dumps({"id": f"{i:064x}", "pubkey": "b" * 64}) + "\n")
        result, calls = self.invoke()
        self.assertEqual(result, 0)
        self.assertEqual([len(json.loads(c[-1])["ids"]) for c in calls], [100, 100, 6])

    def test_manifest_written_before_send_and_survives_lost_ack(self):
        # Import the real publication path without installing its network/crypto dependencies.
        curve = types.ModuleType("coincurve"); curve.PrivateKey = object
        websockets = types.ModuleType("websockets"); websockets.connect = object
        with patch.dict(sys.modules, {"coincurve": curve, "websockets": websockets}):
            smoke = load("smoke_review", KIT / "tests/smoke_test.py")
        path = self.path.parent / "lost-ack.jsonl"
        journal = SmokeManifest(path, RELAY)
        smoke.MANIFEST = journal
        async def send(_):
            self.assertEqual(cleanup.read_manifest(path, RELAY), [self.own["id"]])
        async def lost_ack(*_):
            raise TimeoutError("ACK lost")
        smoke.wait_type = lost_ack
        try:
            with self.assertRaises(TimeoutError):
                asyncio.run(smoke.publish(types.SimpleNamespace(send=send), self.own))
        finally:
            journal.close()
        self.assertEqual(cleanup.read_manifest(path, RELAY), [self.own["id"]])

    def test_failed_journal_write_prevents_transmission(self):
        curve = types.ModuleType("coincurve"); curve.PrivateKey = object
        websockets = types.ModuleType("websockets"); websockets.connect = object
        with patch.dict(sys.modules, {"coincurve": curve, "websockets": websockets}):
            smoke = load("smoke_write_failure", KIT / "tests/smoke_test.py")
        def failed(_):
            raise OSError("disk full")
        smoke.MANIFEST = types.SimpleNamespace(record=failed)
        async def send(_):
            self.fail("must not transmit without a durable ID")
        with self.assertRaises(OSError):
            asyncio.run(smoke.publish(types.SimpleNamespace(send=send), self.own))


if __name__ == "__main__":
    unittest.main()
