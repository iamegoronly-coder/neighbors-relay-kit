#!/usr/bin/env python3
"""Real OpenSSL on loopback with disposable certificates; never contacts a public relay."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

KIT = Path(__file__).resolve().parent.parent


class LocalTLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.openssl = shutil.which(os.environ.get("OPENSSL", "openssl"))
        if not cls.openssl:
            raise unittest.SkipTest("OpenSSL is unavailable")
        result = subprocess.run([cls.openssl, "list", "-kem-algorithms"], capture_output=True, text=True, timeout=10)
        if result.returncode or "ML-KEM" not in result.stdout:
            raise unittest.SkipTest("requires OpenSSL 3.5+ with ML-KEM")
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.cert, cls.key = cls.root / "cert.pem", cls.root / "key.pem"
        subprocess.run([cls.openssl, "req", "-x509", "-newkey", "ed25519", "-noenc",
                        "-keyout", str(cls.key), "-out", str(cls.cert), "-days", "1",
                        "-subj", "/CN=relay.example.org", "-addext", "subjectAltName=DNS:relay.example.org"],
                       check=True, capture_output=True, timeout=10)
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            cls.port = reserve.getsockname()[1]
        cls.server = subprocess.Popen([cls.openssl, "s_server", "-accept", f"127.0.0.1:{cls.port}",
                                       "-cert", str(cls.cert), "-key", str(cls.key), "-tls1_3", "-quiet", "-www"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.stop_server)
        for _ in range(50):
            if cls.server.poll() is not None:
                raise RuntimeError("local TLS server exited")
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=.1):
                    break
            except OSError:
                time.sleep(.05)
        else:
            raise RuntimeError("local TLS server did not start")
        cls.wrapper = cls.root / "openssl"
        cls.wrapper.write_text(f"#!{sys.executable}\n" + '''import os, sys
args = sys.argv[1:]
if args[0] == "s_client":
    args[args.index("-connect") + 1] = "127.0.0.1:" + os.environ["TLS_LOCAL_PORT"]
    if os.environ.get("TLS_LOCAL_TRUST") == "yes": args += ["-CAfile", os.environ["TLS_LOCAL_CERT"]]
os.execv(os.environ["TLS_LOCAL_OPENSSL"], [os.environ["TLS_LOCAL_OPENSSL"], *args])
''')
        cls.wrapper.chmod(0o700)

    @classmethod
    def stop_server(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            cls.server.kill(); cls.server.wait()

    def invoke(self, host="relay.example.org", trust=True):
        env = dict(os.environ, OPENSSL=str(self.wrapper), TLS_LOCAL_PORT=str(self.port),
                   TLS_LOCAL_OPENSSL=self.openssl, TLS_LOCAL_CERT=str(self.cert), TLS_LOCAL_TRUST="yes" if trust else "no")
        return subprocess.run(["sh", str(KIT / "scripts/check-pq-tls.sh"), "--timeout", "5", host],
                              env=env, text=True, capture_output=True, timeout=18)

    def test_trusted_matching_certificate_passes_both_groups(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("PASS"), 2)

    def test_trusted_wrong_hostname_fails_both_groups(self):
        result = self.invoke(host="wrong.example.org")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("FAIL"), 2)

    def test_untrusted_certificate_fails_both_groups(self):
        result = self.invoke(trust=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("FAIL"), 2)


if __name__ == "__main__":
    unittest.main()
