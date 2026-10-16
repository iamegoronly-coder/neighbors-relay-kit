#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import subprocess
import unittest

spec = importlib.util.spec_from_file_location('key', Path(__file__).resolve().parents[1] / 'scripts/verify-caddy-key.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def listing(fingerprint=module.FINGERPRINT, validity='-', expiry=''):
    return f'pub:{validity}:4096:1:ID:1459530465:{expiry}::-:::scSC:\nfpr:::::::::{fingerprint}:\n'


class CaddyKey(unittest.TestCase):
    def test_pinned_primary_with_subkeys(self):
        self.assertEqual(module.validate_listing(listing() + 'sub:e:2048:1:ID:1:2:::::e:\nfpr:::::::::OTHER:\n'), module.FINGERPRINT)

    def test_wrong_missing_multiple_or_malformed_primary(self):
        for text in ('', listing('0' * 40), listing() + listing('0' * 40), listing() + listing(),
                     'fpr:::::::::' + module.FINGERPRINT + ':', 'pub:-:\n', 'pub:-:4096:1:ID:1:::-:::s:\nsub:-:\n' + listing()):
            with self.subTest(text=text), self.assertRaises(ValueError):
                module.validate_listing(text)

    def test_revoked_expired_disabled_primary(self):
        for text in (listing(validity='r'), listing(validity='e'), listing(validity='d'), listing(expiry='1'), listing(expiry='bad')):
            with self.assertRaises(ValueError): module.validate_listing(text, now=10)

    def test_gpg_failure_and_private_keyring(self):
        def run(args, **kwargs):
            self.assertIn('--no-options', args)
            self.assertIn('--show-keys', args)
            self.assertNotIn('--import', args)
            home = Path(args[args.index('--homedir') + 1])
            self.assertEqual(home.stat().st_mode & 0o777, 0o700)
            raise subprocess.CalledProcessError(2, args)
        with self.assertRaises(subprocess.CalledProcessError): module.verify('/tmp/test.key', runner=run)


if __name__ == '__main__':
    unittest.main()
