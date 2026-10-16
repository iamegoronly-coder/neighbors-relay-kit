#!/usr/bin/env python3
"""Exercise the actual CLI with a fake OpenSSL; no network or server changes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parent.parent


class TLSTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fake = Path(self.temp.name) / "openssl"
        self.fake.write_text(f"#!{sys.executable}\n" + '''import os, sys, time
args = sys.argv[1:]
mode = os.environ.get("TLS_TEST_MODE", "success")
if args[0] == "list":
    print("unavailable" if mode == "unsupported" else "ML-KEM-768")
    sys.exit(0)
assert args[args.index("-verify_hostname") + 1] == "relay.example.org"
assert "-verify_return_error" in args and "-tls1_3" in args
if mode == "timeout": time.sleep(10)
group = args[args.index("-groups") + 1]
if mode == "wrong_group": group = "P-256"
print("Negotiated TLS1.3 group: " + group)
if mode != "unverified": print("Verification: OK")
sys.exit(1 if mode == "failed_exit" else 0)
''')
        self.fake.chmod(0o700)

    def invoke(self, mode, timeout="2"):
        env = dict(os.environ, OPENSSL=str(self.fake), TLS_TEST_MODE=mode)
        return subprocess.run(["sh", str(KIT / "scripts/check-pq-tls.sh"), "--timeout", timeout,
                               "relay.example.org"], capture_output=True, text=True, env=env, timeout=10)

    def test_both_groups_and_required_verification_flags(self):
        result = self.invoke("success")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("PASS"), 2)

    def test_failed_process_cannot_pass_from_positive_output(self):
        result = self.invoke("failed_exit")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("PASS", result.stdout)

    def test_unverified_certificate_fails(self):
        self.assertEqual(self.invoke("unverified").returncode, 1)

    def test_wrong_group_fails(self):
        self.assertEqual(self.invoke("wrong_group").returncode, 1)

    def test_timeout_returns_failure(self):
        result = self.invoke("timeout", "1.5")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("timed out"), 2)

    def test_unsupported_openssl_is_distinct(self):
        self.assertEqual(self.invoke("unsupported").returncode, 2)

    def test_invalid_timeout(self):
        self.assertEqual(self.invoke("success", "nan").returncode, 2)


if __name__ == "__main__":
    unittest.main()
