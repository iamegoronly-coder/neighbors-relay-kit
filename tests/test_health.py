#!/usr/bin/env python3
"""Health policy checks, without touching services, clocks or production data."""
import importlib.machinery
import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path

loader = importlib.machinery.SourceFileLoader("relay_health", str(Path(__file__).resolve().parent.parent / "bin" / "strfry-health"))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
now = datetime(2026, 9, 25, tzinfo=timezone.utc)
baseline = dict(relay_active=True, loopback_metrics_ok=True, prune_timer_active=True,
                disk_guard_timer_active=True, ntp_synchronized=True, data_bytes=1000,
                filesystem_free_bytes=4 * 1024**3, last_prune_utc=now.isoformat())
assert module.health_errors(baseline, now) == []
cases = [
    {"last_prune_utc": None}, {"last_prune_utc": "bad"},
    {"last_prune_utc": (now-timedelta(seconds=301)).isoformat()},
    {"last_prune_utc": (now+timedelta(seconds=31)).isoformat()},
    {"prune_timer_active": False}, {"disk_guard_timer_active": False},
    {"ntp_synchronized": False}, {"relay_active": False}, {"loopback_metrics_ok": False},
    {"data_bytes": module.MAX_DATABASE_BYTES},
    {"filesystem_free_bytes": module.MIN_FREE_BYTES},
]
for changes in cases:
    assert module.health_errors(baseline | changes, now), changes
print(f"PASS healthy baseline and {len(cases)} operational failures")
