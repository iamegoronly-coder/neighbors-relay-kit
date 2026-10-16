#!/usr/bin/env python3
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify_binary', ROOT / 'scripts/verify-binary.py')
verify_binary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_binary)


def executable(machine=62):
    header = bytearray(64)
    header[:7] = b'\x7fELF\x02\x01\x01'
    header[16:18] = (3).to_bytes(2, 'little')
    header[18:20] = machine.to_bytes(2, 'little')
    return bytes(header) + b'fixture bytes, never executed'


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.binary = Path(self.temp.name) / 'strfry'
        self.binary.write_bytes(executable())
        self.digest = hashlib.sha256(self.binary.read_bytes()).hexdigest()

    def test_exact_hash(self):
        self.assertEqual(verify_binary.verify(self.binary, self.digest), self.digest)

    def test_corruption_refused(self):
        self.binary.write_bytes(executable() + b'changed')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            verify_binary.verify(self.binary, self.digest)

    def test_other_architecture_refused_even_with_matching_hash(self):
        self.binary.write_bytes(executable(183))  # AArch64
        with self.assertRaisesRegex(ValueError, 'x86_64'):
            verify_binary.verify(self.binary, hashlib.sha256(self.binary.read_bytes()).hexdigest())

    def test_script_refused_without_execution(self):
        self.binary.write_bytes(b'#!/bin/sh\necho do-not-run\n')
        with self.assertRaisesRegex(ValueError, 'executable'):
            verify_binary.verify(self.binary, hashlib.sha256(self.binary.read_bytes()).hexdigest())

    def test_malformed_expected_hash(self):
        for value in ('', 'a' * 63, 'A' * 64, 'z' * 64, '../checksum'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify_binary.verify(self.binary, value)

    def test_comparison_detects_same_length_change(self):
        other = self.binary.with_name('other')
        other.write_bytes(self.binary.read_bytes())
        command = [sys.executable, str(ROOT / 'scripts/compare-binaries.py'), str(self.binary), str(other)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        other.write_bytes(other.read_bytes()[:-1] + b'X')
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        other.unlink()
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)

    def test_install_requires_explicit_checksum(self):
        # Invalid arguments fail before root checks, filesystem changes or any service command.
        for args in (['--binary', str(self.binary)], ['--sha256', self.digest], ['--unknown'], ['--binary', '', '--sha256', '']):
            with self.subTest(args=args):
                result = subprocess.run(['sh', str(ROOT / 'scripts/install.sh'), *args], capture_output=True)
                self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
