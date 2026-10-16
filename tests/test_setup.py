#!/usr/bin/env python3
"""Wizard tests: all package/service/network operations are explicit test doubles."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_relay', KIT / 'scripts/setup-relay.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def elf():
    data = bytearray(80)
    data[:7] = b'\x7fELF\x02\x01\x01'
    data[16:18] = (3).to_bytes(2, 'little')
    data[18:20] = (62).to_bytes(2, 'little')
    return bytes(data)


class FakeRunner:
    def __init__(self, root):
        self.root, self.calls = root, []
        self.https_ok, self.metrics_status, self.reload_fail = True, '404', False
        self.fail_apt, self.bad_info, self.health_fail = False, False, False
        self.fingerprint = module.key_verifier.FINGERPRINT

    def run(self, args, *, capture=False, check=True, **kwargs):
        args = [str(a) for a in args]
        self.calls.append(args)
        text, code = '', 0
        if args[0] == 'timedatectl':
            text = 'yes\n'
        elif args[0] == 'apt-get':
            if self.fail_apt:
                raise subprocess.CalledProcessError(100, args)
            if any(a.startswith('caddy=') for a in args):
                path = self.root / 'etc/caddy/Caddyfile'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(':80 { respond "package default" }')
        elif args[0] == 'gpg' and '--show-keys' in args:
            text = 'pub:-:4096:1:ID:1459530465:::-:::scSC:\nfpr:::::::::' + self.fingerprint + ':\n'
        elif args[0] == 'gpg':
            Path(args[args.index('--output') + 1]).write_bytes(b'test-keyring')
        elif args[0] == 'curl' and 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' in args:
            Path(args[args.index('-o') + 1]).write_bytes(b'test-key')
        elif args[0] == 'curl':
            assert '--resolve' in args and '--noproxy' in args
            assert '-k' not in args and '--insecure' not in args
            if not self.https_ok:
                code = 60
            elif args[-1].endswith('/metrics'):
                text = self.metrics_status
            else:
                text = '{}' if self.bad_info else json.dumps({'limitation': {'max_subscriptions': 20}, 'supported_nips': [1, 40]})
        elif args[0] == 'sh' and args[1].endswith('/build-strfry.sh'):
            path = self.root / 'opt/strfry-src/strfry'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(elf())
        elif args[0] == 'sh' and args[1].endswith('/install.sh'):
            assert '--no-start' in args
            executable = Path(args[args.index('--binary') + 1])
            expected = args[args.index('--sha256') + 1]
            module.verifier.verify(executable, expected)
            destination = self.root / 'usr/local/bin/strfry'
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(executable, destination)
        elif args[:3] == ['systemctl', 'reload', 'caddy'] and self.reload_fail:
            self.reload_fail = False
            raise subprocess.CalledProcessError(1, args)
        elif args[0].endswith('/strfry-health') and self.health_fail:
            raise subprocess.CalledProcessError(1, args)
        if check and code:
            raise subprocess.CalledProcessError(code, args)
        return subprocess.CompletedProcess(args, code, text, 'certificate unavailable' if code else '')


class SetupTests(unittest.TestCase):
    def setUp(self):
        module.LANGUAGE = "ru"
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'host'
        for directory in ('etc', 'run/systemd/system', 'run/lock', 'proc/net', 'var/lib', 'usr/share/keyrings', 'etc/apt/sources.list.d'):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        (self.root / 'etc/os-release').write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
        (self.root / 'proc/meminfo').write_text('MemTotal: 1048576 kB\nSwapTotal: 0 kB\n')
        self.runner = FakeRunner(self.root)
        self.setup = module.Setup(KIT, self.root, self.runner)
        self.binary = Path(self.temp.name) / 'binary'
        self.binary.write_bytes(elf())
        self.sha = hashlib.sha256(elf()).hexdigest()
        for target, value in [('os.geteuid', 0), ('platform.machine', 'x86_64'),
                              ('shutil.disk_usage', shutil._ntuple_diskusage(20 * module.GIB, 0, 20 * module.GIB)),
                              ('socket.getaddrinfo', [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('192.0.2.1', 443))])]:
            # Patch specific functions, not an entire filesystem/network module.
            part, attribute = target.split('.')
            item = patch.object(getattr(module, part), attribute, return_value=value)
            item.start()
            self.addCleanup(item.stop)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)
        self.umask = patch.object(module.os, 'umask')
        self.umask.start()
        self.addCleanup(self.umask.stop)

    def run_install(self, mode='binary'):
        self.setup.install(mode, 'relay.example.org', self.binary, self.sha, 0)

    def state(self):
        return json.loads((self.root / 'var/lib/neighbors-relay-setup/state.json').read_text())

    def test_domain_validation(self):
        self.assertEqual(module.domain_name('Relay.Example.org.'), 'relay.example.org')
        for name in ('https://relay.example.org', 'relay.example.org/relay', 'x\nadmin off', '*.example.org',
                     '127.0.0.1', '::1', 'example.org:443', '-bad.example.org', 'a' * 64 + '.org'):
            with self.subTest(name=name), self.assertRaises(module.SetupError):
                module.domain_name(name)

    def test_preflight_is_read_only(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(self.setup.preflight('binary', 'relay.example.org'), ['192.0.2.1'])
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))
        self.assertEqual(self.runner.calls, [['timedatectl', 'show', '-p', 'NTPSynchronized', '--value']])

    def test_existing_config_refused(self):
        (self.root / 'etc/caddy').mkdir()
        with self.assertRaisesRegex(module.SetupError, 'существующая'):
            self.setup.preflight('binary', 'relay.example.org')
        self.assertEqual(self.runner.calls, [])

    def test_busy_ipv6_port_refused(self):
        (self.root / 'proc/net/tcp6').write_text('header\n0: 00000000000000000000000000000000:01BB 0:0 0A\n')
        with self.assertRaisesRegex(module.SetupError, '443'):
            self.setup.preflight('binary', 'relay.example.org')

    def test_source_memory_and_disk_requirements(self):
        with self.assertRaisesRegex(module.SetupError, '2,5'):
            self.setup.preflight('source', 'relay.example.org')
        (self.root / 'proc/meminfo').write_text('MemTotal: 1048576 kB\nSwapTotal: 2097152 kB\n')
        self.setup.preflight('source', 'relay.example.org')
        with patch.object(module.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(10, 9, 1)):
            with self.assertRaisesRegex(module.SetupError, 'свободного'):
                self.setup.preflight('binary', 'relay.example.org')

    def test_dns_failure_before_writes(self):
        with patch.object(module.socket, 'getaddrinfo', side_effect=socket.gaierror('not found')):
            with self.assertRaisesRegex(module.SetupError, 'DNS'):
                self.setup.preflight('binary', 'relay.example.org')
        self.assertFalse((self.root / 'var/lib/neighbors-relay-setup').exists())

    def test_binary_requires_hash_and_corruption_refused(self):
        with self.assertRaises(module.SetupError):
            self.setup.candidate(self.binary, None)
        with self.assertRaises(ValueError):
            self.setup.candidate(self.binary, '0' * 64)
        self.assertEqual(self.runner.calls, [])

    def test_binary_full_sequence_and_no_build(self):
        self.run_install()
        self.assertEqual(self.state()['phase'], 'complete')
        self.assertEqual((self.root / 'usr/local/bin/strfry').read_bytes(), elf())
        self.assertFalse(any('/build-strfry.sh' in ' '.join(c) for c in self.runner.calls))
        self.assertIn(['apt-mark', 'hold', 'caddy'], self.runner.calls)
        config = (self.root / 'etc/caddy/Caddyfile').read_text()
        self.assertIn('relay.example.org', config)
        self.assertIn('127.0.0.1:7777', config)

    def test_source_path_builds_then_installs(self):
        self.run_install('source')
        calls = [' '.join(c) for c in self.runner.calls]
        self.assertLess(next(i for i,c in enumerate(calls) if '/build-strfry.sh' in c),
                        next(i for i,c in enumerate(calls) if '/install.sh' in c))
        self.assertEqual(self.state()['binary_sha256'], self.sha)

    def test_wrong_caddy_key_never_installs_trust_or_repository(self):
        self.runner.fingerprint = '0' * 40
        with self.assertRaisesRegex(module.SetupError, 'ключа Caddy'):
            self.run_install()
        self.assertFalse((self.root / 'usr/share/keyrings/caddy-stable-archive-keyring.gpg').exists())
        self.assertFalse((self.root / 'etc/apt/sources.list.d/caddy-stable.list').exists())
        self.assertFalse(any(c[0] == 'gpg' and '--dearmor' in c for c in self.runner.calls))
        self.assertFalse(any(c[0] == 'apt-get' and 'caddy=2.11.7' in c for c in self.runner.calls))

    def test_each_language_runs_the_same_binary_installation(self):
        # Other full-path tests cover RU; these exercise the translated formatting at runtime.
        for lang in ('en', 'de'):
            module.LANGUAGE = lang
            self.run_install()
            self.assertEqual(self.state()['phase'], 'complete')
            self.assertEqual((self.root / 'usr/local/bin/strfry').read_bytes(), elf())

    def test_caddy_reload_restores_package_default(self):
        self.runner.reload_fail = True
        with self.assertRaisesRegex(module.SetupError, 'Восстановлен'):
            self.run_install()
        self.assertEqual((self.root / 'etc/caddy/Caddyfile').read_text(), ':80 { respond "package default" }')
        self.assertNotEqual(self.state()['phase'], 'complete')

    def test_certificate_timeout_keeps_services_for_check(self):
        self.runner.https_ok = False
        with self.assertRaisesRegex(module.SetupError, '--check'):
            self.run_install()
        self.assertEqual(self.state()['phase'], 'services_installed')
        self.runner.https_ok = True
        before = len(self.runner.calls)
        self.setup.check('relay.example.org', 0)
        self.assertFalse(any(c[0] in ('apt-get', 'apt-mark') for c in self.runner.calls[before:]))

    def test_metrics_or_wrong_nip11_not_success(self):
        for field, value in [('metrics_status', '200'), ('bad_info', True), ('health_fail', True)]:
            with self.subTest(field=field):
                setattr(self.runner, field, value)
                with self.assertRaises((module.SetupError, subprocess.CalledProcessError)):
                    self.setup.check('relay.example.org', 0)
                setattr(self.runner, field, '404' if field == 'metrics_status' else False)

    def test_apt_failure_does_not_publish_or_install_relay(self):
        self.runner.fail_apt = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_install()
        self.assertFalse((self.root / 'usr/local/bin/strfry').exists())
        self.assertFalse((self.root / 'etc/caddy').exists())
        self.assertEqual(self.state()['phase'], 'started')

    def test_plan_and_decline_leave_host_unchanged(self):
        args = ['--lang', 'ru', '--domain', 'relay.example.org', '--mode', 'binary', '--binary', str(self.binary), '--sha256', self.sha]
        for extra in (['--plan'], []):
            with self.subTest(extra=extra), patch.object(module, 'Setup', return_value=self.setup), \
                    patch.object(module.sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='нет'):
                self.assertEqual(module.main([*args, *extra]), 0)
                self.assertFalse((self.root / 'var/lib/neighbors-relay-setup').exists())
                self.assertFalse(any(c[0] == 'apt-get' for c in self.runner.calls))


if __name__ == '__main__':
    unittest.main()
