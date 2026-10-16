"""Durable ID journal written BEFORE sending each event, including rejected/lost-ACK attempts."""
import json
import os
import secrets


class SmokeManifest:
    def __init__(self, path, relay):
        # Exclusive creation prevents overwriting an earlier run, even after a crash.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.file = os.fdopen(descriptor, "w", encoding="utf-8")
        self.seen = set()
        try:
            self._append({"version": 1, "relay": relay, "run_id": secrets.token_hex(16)})
        except BaseException:
            self.file.close()
            raise

    def _append(self, value):
        self.file.write(json.dumps(value, separators=(",", ":")) + "\n")
        self.file.flush()
        os.fsync(self.file.fileno())

    def record(self, event):
        if event["id"] not in self.seen:
            self._append({"id": event["id"], "pubkey": event["pubkey"]})
            self.seen.add(event["id"])

    def close(self):
        self.file.close()
