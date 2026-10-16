#!/usr/bin/env python3
"""Execute documentation blocks with fake package/service tools, never real apt or /etc writes."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parent.parent
DOC = (KIT / "docs/caddy.md").read_text()


def block(heading):
    return re.search(r"```sh\n(.*?)\n```", DOC.split(heading, 1)[1], re.S)[1]


class CaddyInstructionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backup = self.root / "backup"
        package = self.backup / "package"
        package.mkdir(parents=True)
        (self.backup / "etc-caddy").mkdir()
        (self.backup / "package-version").write_text("2.11.7\n")
        self.deb = package / "caddy_2.11.7_amd64.deb"
        self.deb.write_bytes(b"test package; not installable")
        (package / "SHA256SUMS").write_text(hashlib.sha256(self.deb.read_bytes()).hexdigest() + "  ./" + self.deb.name + "\n")
        (self.root / "held").write_text("yes")
        (self.root / "installed").write_text("2.11.7")
        fakebin = self.root / "bin"
        fakebin.mkdir()
        driver = f"#!{sys.executable}\n" + '''import hashlib, json, os, pathlib, sys
root = pathlib.Path(os.environ["CADDY_TEST_ROOT"])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "calls").open("a") as stream: stream.write(json.dumps([name, *args]) + "\\n")
if name == "apt-mark":
    (root / "held").write_text("yes" if args[0] == "hold" else "no")
elif name == "apt-get":
    assert (root / "held").read_text() == "no", "held package update would fail"
    if os.environ.get("CADDY_TEST_FAIL") == "1": sys.exit(42)
    target = args[-1]
    if target.startswith("caddy="): version = target.split("=", 1)[1]
    else:
        assert pathlib.Path(target) == root / "backup/package/caddy_2.11.7_amd64.deb", target
        version = "2.11.7"
    (root / "installed").write_text(version)
elif name == "dpkg-query": print((root / "installed").read_text())
elif name == "dpkg-deb": print("caddy" if args[-1] == "Package" else "2.11.7")
elif name == "sha256sum":
    digest, filename = pathlib.Path(args[-1]).read_text().split()
    if hashlib.sha256(pathlib.Path(filename).read_bytes()).hexdigest() != digest: sys.exit(1)
elif name in ("cp", "cmp", "systemctl", "sleep", "caddy", "journalctl"):
    # No real file copy, service command or package installation is performed.
    pass
else: raise AssertionError(name)
'''
        for name in ("apt-mark", "apt-get", "dpkg-query", "dpkg-deb", "sha256sum", "cp", "cmp", "systemctl", "sleep", "caddy", "journalctl"):
            path = fakebin / name
            path.write_text(driver)
            path.chmod(0o700)
        (self.backup / "caddy").write_text(driver)
        (self.backup / "caddy").chmod(0o700)
        self.env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ["PATH"],
                        BK=str(self.backup), V="2.12.0", CADDY_TEST_ROOT=str(self.root))

    def run_block(self, heading, fail=False):
        env = dict(self.env, CADDY_TEST_FAIL="1" if fail else "0")
        result = subprocess.run(["sh", "-c", block(heading)], env=env,
                                capture_output=True, text=True, timeout=10)
        self.calls = [json.loads(line) for line in (self.root / "calls").read_text().splitlines()]
        return result

    def test_upgrade_unholds_then_installs_and_reholds(self):
        result = self.run_block("### 4. Install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "installed").read_text(), "2.12.0")
        self.assertEqual((self.root / "held").read_text(), "yes")

    def test_failed_upgrade_reholds_and_does_not_restart(self):
        result = self.run_block("### 4. Install", fail=True)
        self.assertEqual(result.returncode, 42)
        self.assertEqual((self.root / "held").read_text(), "yes")
        self.assertFalse(any(call[:2] == ["systemctl", "restart"] for call in self.calls))

    def test_rollback_uses_exact_saved_package_and_reholds(self):
        (self.root / "installed").write_text("2.12.0")
        result = self.run_block("### Rollback to the exact saved package")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "installed").read_text(), "2.11.7")
        self.assertEqual((self.root / "held").read_text(), "yes")
        self.assertEqual([c[-1] for c in self.calls if c[0] == "apt-get"], [str(self.deb)])

    def test_failed_rollback_reholds_and_does_not_restart(self):
        result = self.run_block("### Rollback to the exact saved package", fail=True)
        self.assertEqual(result.returncode, 42)
        self.assertEqual((self.root / "held").read_text(), "yes")
        self.assertFalse(any(call[:2] == ["systemctl", "restart"] for call in self.calls))

    def test_corrupt_saved_package_is_rejected_before_changes(self):
        self.deb.write_bytes(b"corrupt")
        result = self.run_block("### Rollback to the exact saved package")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[0] in ("apt-get", "apt-mark", "cp") for c in self.calls))

    def test_all_documented_shell_blocks_parse(self):
        for code in re.findall(r"```sh\n(.*?)\n```", DOC, re.S):
            result = subprocess.run(["sh", "-n"], input=code, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
