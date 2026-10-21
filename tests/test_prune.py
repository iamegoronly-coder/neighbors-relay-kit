#!/usr/bin/env python3
"""Age maintenance must not start a full scan or report success after failure."""
import importlib.machinery
import importlib.util
import re
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parent.parent / "bin" / "strfry-prune-events"
loader = importlib.machinery.SourceFileLoader("strfry_prune_events", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class PruneTests(unittest.TestCase):
    def test_indexed_age_only_and_no_scan(self):
        for age in (93600, 1):
            args = [str(path), "--binary", "/fake/strfry", "--config", "/fake/config",
                    "--age-seconds", str(age)]
            with patch.object(module.subprocess, "run") as run, \
                 patch.object(module.subprocess, "Popen") as scan, \
                 patch("sys.argv", args):
                self.assertEqual(module.main(), 0)
            run.assert_called_once_with(
                ["/fake/strfry", "--config", "/fake/config", "--verbosity=WARNING",
                 "delete", "--age", str(age)], check=True, stdout=subprocess.DEVNULL)
            scan.assert_not_called()

    def test_failure_propagates_so_systemd_does_not_stamp_success(self):
        with patch.object(module.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "delete")), \
             patch("sys.argv", [str(path)]), patch("builtins.print") as output:
            with self.assertRaises(subprocess.CalledProcessError):
                module.main()
            output.assert_not_called()
        unit = (path.parent.parent / "systemd/strfry-prune.service").read_text()
        self.assertIn("ExecStart=/usr/local/libexec/strfry-prune-events", unit)
        self.assertIn("ExecStartPost=/usr/local/libexec/strfry-prune-stamp", unit)

    def test_default_age_matches_relay_configuration(self):
        config = (path.parent.parent / "config/strfry.conf").read_text()
        match = re.search(r"^\s*rejectEventsOlderThanSeconds = (\d+)$", config, re.M)
        self.assertIsNotNone(match)
        with patch.object(module.subprocess, "run") as run, patch("sys.argv", [str(path)]):
            self.assertEqual(module.main(), 0)
        self.assertEqual(run.call_args.args[0][-1], match.group(1))
        self.assertEqual(match.group(1), "93600")

    def test_invalid_age_does_not_delete_anything(self):
        with patch.object(module.subprocess, "run") as run, patch("sys.argv", [str(path), "--age-seconds", "0"]):
            with self.assertRaises(SystemExit) as exit:
                module.main()
            self.assertEqual(exit.exception.code, 2)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
