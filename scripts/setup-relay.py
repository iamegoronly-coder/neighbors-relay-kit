#!/usr/bin/env python3
"""First installation on a clean Ubuntu 24.04 x86_64 VPS. Never updates an existing relay."""
import argparse
import fcntl
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

KIT = Path(__file__).resolve().parents[1]
GIB = 1024 ** 3
UNITS = ['strfry.service', 'strfry-prune.timer', 'strfry-disk-guard.timer']
RUNTIME = ['ca-certificates', 'curl', 'gnupg', 'debian-keyring', 'debian-archive-keyring',
           'apt-transport-https', 'git', 'binutils', 'python3', 'liblmdb0', 'libssl3t64',
           'zlib1g', 'libsecp256k1-1', 'libzstd1', 'libstdc++6']
spec = importlib.util.spec_from_file_location('verify_binary', KIT / 'scripts/verify-binary.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
key_spec = importlib.util.spec_from_file_location('verify_caddy_key', KIT / 'scripts/verify-caddy-key.py')
key_verifier = importlib.util.module_from_spec(key_spec)
key_spec.loader.exec_module(key_verifier)


LANGUAGE = 'ru'
CATALOGS = {lang: json.loads((KIT / 'scripts/locales' / (lang + '.json')).read_text())
            for lang in ('en', 'ru', 'de')}


def tr(key, **values):
    return CATALOGS[LANGUAGE][key].format(**values)


def choose_language(argv):
    global LANGUAGE
    locale = next((os.environ[name] for name in ('LC_ALL', 'LC_MESSAGES', 'LANG') if os.environ.get(name)), 'en')
    default = locale.lower().split('_')[0].split('-')[0].split('.')[0]
    default = default if default in CATALOGS else 'en'
    early = argparse.ArgumentParser(add_help=False)
    early.add_argument('--lang', choices=tuple(CATALOGS))
    choice, _ = early.parse_known_args(argv)
    LANGUAGE = choice.lang or default
    if choice.lang is None and not argv and sys.stdin.isatty():
        answer = input('Language / Sprache / Язык [en/ru/de] (' + default + '): ').strip().lower()
        if answer and answer not in CATALOGS:
            raise SetupError('Choose / Wählen Sie / Выберите: en, ru, de')
        LANGUAGE = answer or default


class SetupError(Exception):
    pass


def domain_name(value):
    try:
        name = value.strip().rstrip('.').encode('idna').decode('ascii').lower()
    except UnicodeError as error:
        raise SetupError(tr('invalid_domain')) from error
    labels = name.split('.')
    if (len(name) > 253 or len(labels) < 2 or labels[-1].isdigit()
            or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part) for part in labels)):
        raise SetupError(tr('domain_format'))
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return name
    raise SetupError(tr('domain_not_ip'))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Runner:
    def run(self, args, *, capture=False, check=True, timeout=900, env=None):
        return subprocess.run([str(x) for x in args], text=True, capture_output=capture,
                              check=check, timeout=timeout, env=env)


class Setup:
    def __init__(self, kit=KIT, root=Path('/'), runner=None):
        # root injection is for unit tests only; no CLI/env override exposes it to an installation.
        self.kit, self.root = Path(kit), Path(root)
        self.runner = runner or Runner()
        self.stage = tr('preparation')
        self.started = False

    def path(self, value):
        return self.root / value.lstrip('/')

    def run(self, args, **kwargs):
        return self.runner.run(args, **kwargs)

    def metadata(self):
        data = json.loads((self.kit / 'release/local-candidate.json').read_text())
        if not re.fullmatch(r'\d+\.\d+\.\d+', data['caddy_version']):
            raise SetupError(tr('invalid_caddy_version'))
        return data

    def candidate(self, binary, expected):
        if binary:
            if not expected:
                raise SetupError(tr('custom_binary_checksum'))
            path = Path(binary).expanduser().resolve()
        else:
            if expected:
                raise SetupError(tr('checksum_requires_binary'))
            data = self.metadata()
            if digest(self.kit / 'patch/strfry-neighbors.patch') != data['patch_sha256']:
                raise SetupError(tr('patch_changed'))
            candidates = [self.kit / 'payload/strfry',
                          self.kit / 'out' / data['version'] / 'strfry']
            path = next((p for p in candidates if p.is_file()), None)
            if path is None:
                raise SetupError(tr('binary_missing'))
            expected = data['sha256']
        verifier.verify(path, expected)
        return path, expected

    def preflight(self, mode, domain):
        if os.geteuid() != 0:
            raise SetupError(tr('run_as_root'))
        os_release = self.path('/etc/os-release').read_text()
        fields = dict(line.split('=', 1) for line in os_release.splitlines() if '=' in line)
        if (fields.get('ID', '').strip('"') != 'ubuntu'
                or fields.get('VERSION_ID', '').strip('"') != '24.04'
                or platform.machine() != 'x86_64'):
            raise SetupError(tr('supported_platform'))
        if not self.path('/run/systemd/system').is_dir():
            raise SetupError(tr('systemd_required'))
        guarded = ['/etc/caddy', '/var/lib/strfry', '/etc/strfry', '/usr/local/bin/strfry',
                   '/etc/apt/sources.list.d/caddy-stable.list',
                   '/usr/share/keyrings/caddy-stable-archive-keyring.gpg',
                   '/var/lib/neighbors-relay-setup', '/usr/bin/caddy', '/usr/local/bin/caddy',
                   '/etc/systemd/journald@strfry.conf']
        guarded += ['/usr/local/libexec/' + helper for helper in
                    ('strfry-disk-guard', 'strfry-prune-stamp', 'strfry-prune-events',
                     'strfry-ephemeral-policy', 'strfry-health', 'strfry-cleanup-smoke-events')]
        guarded += [f'{directory}/{unit}' for directory in ('/etc/systemd/system', '/lib/systemd/system',
                    '/usr/lib/systemd/system') for unit in [*UNITS, 'strfry-prune.service', 'strfry-disk-guard.service']]
        for name in guarded:
            path = self.path(name)
            if path.exists() or path.is_symlink():
                raise SetupError(tr('existing_installation', v0=name))
        if self.root == Path('/') and shutil.which('caddy'):
            raise SetupError(tr('caddy_exists'))
        for filename in ('tcp', 'tcp6'):
            path = self.path('/proc/net/' + filename)
            if not path.exists():
                continue
            for line in path.read_text().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 4 and parts[3] == '0A':
                    port = int(parts[1].rsplit(':', 1)[1], 16)
                    if port in (80, 443, 7777):
                        raise SetupError(tr('port_busy', v0=port))
        memory = {}
        for line in self.path('/proc/meminfo').read_text().splitlines():
            parts = line.split()
            if parts[0] in ('MemTotal:', 'SwapTotal:'):
                memory[parts[0][:-1]] = int(parts[1]) * 1024
        if memory.get('MemTotal', 0) < 768 * 1024 ** 2:
            raise SetupError(tr('ram_required'))
        if mode == 'source' and sum(memory.values()) < 2.5 * GIB:
            raise SetupError(tr('build_ram_required'))
        required = (6 if mode == 'source' else 4) * GIB
        if shutil.disk_usage(self.path('/var/lib')).free < required:
            raise SetupError(tr('disk_required', v0=required // GIB))
        if mode == 'source':
            if shutil.disk_usage(self.path('/opt')).free < 6 * GIB:
                raise SetupError(tr('build_disk_required'))
            source = self.path('/opt/strfry-src')
            if source.exists() or source.is_symlink():
                raise SetupError(tr('source_exists'))
        ntp = self.run(['timedatectl', 'show', '-p', 'NTPSynchronized', '--value'], capture=True)
        if ntp.stdout.strip() != 'yes':
            raise SetupError(tr('ntp_required'))
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)})
        except socket.gaierror as error:
            raise SetupError(tr('dns_failed')) from error
        return addresses

    def plan(self, mode, domain, addresses, binary=None):
        print(tr('relay_addresses', v0=domain, v1=', '.join(addresses)), flush=True)
        print(tr('verify_dns'))
        print(tr('method_label') + (tr('binary_method') if mode == 'binary' else
                            tr('source_method')))
        if binary:
            print(tr('binary_path', v0=binary))
        print(tr('caddy_plan', v0=self.metadata()['caddy_version']))
        print(tr('installation_plan'), flush=True)

    def write_state(self, domain, phase, expected=None):
        folder = self.path('/var/lib/neighbors-relay-setup')
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        data = {'domain': domain, 'phase': phase, 'binary_sha256': expected}
        temp = folder / 'state.json.tmp'
        temp.write_text(json.dumps(data, indent=2) + '\n')
        temp.chmod(0o600)
        os.replace(temp, folder / 'state.json')

    def apt(self, *args):
        env = dict(os.environ, DEBIAN_FRONTEND='noninteractive', NEEDRESTART_MODE='l')
        self.run(['apt-get', '-o', 'DPkg::Lock::Timeout=600', '-o', 'APT::Update::Error-Mode=any', *args], env=env, timeout=3600)

    def configure_caddy(self, domain, work):
        config = (self.kit / 'config/Caddyfile.example').read_text().replace('relay.example.org', domain)
        candidate = work / 'Caddyfile'
        candidate.write_text(config)
        self.run(['caddy', 'validate', '--config', candidate, '--adapter', 'caddyfile'])
        target = self.path('/etc/caddy/Caddyfile')
        backup = self.path('/var/lib/neighbors-relay-setup/Caddyfile.package-default')
        shutil.copy2(target, backup)
        shutil.copyfile(candidate, target)
        target.chmod(0o644)
        try:
            self.run(['systemctl', 'reload', 'caddy'])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            shutil.copyfile(backup, target)
            self.run(['systemctl', 'reload', 'caddy'], check=False)
            raise SetupError(tr('caddy_restored'))

    def install(self, mode, domain, binary, expected, tls_timeout):
        self.started = True
        self.stage = tr('preparing_files')
        os.umask(0o077)
        self.write_state(domain, 'started', expected)
        with tempfile.TemporaryDirectory(prefix='neighbors-setup-') as temp:
            work = Path(temp)
            staged = work / 'strfry'
            if mode == 'binary':
                shutil.copyfile(binary, staged)
                verifier.verify(staged, expected)  # Verify a private snapshot, not a mutable original.
            self.stage = tr('installing_dependencies')
            print(tr('dependencies_progress'), flush=True)
            self.apt('update')
            self.apt('install', '-y', '--no-install-recommends', *RUNTIME)
            if mode == 'source':
                self.stage = tr('building_sources')
                print(tr('build_progress'), flush=True)
                env = dict(os.environ, SRC=str(self.path('/opt/strfry-src')), DEBIAN_FRONTEND='noninteractive', NEEDRESTART_MODE='l')
                self.run(['sh', self.kit / 'scripts/build-strfry.sh'], env=env, timeout=7200)
                shutil.copyfile(self.path('/opt/strfry-src/strfry'), staged)
                expected = digest(staged)
                verifier.verify(staged, expected)
            else:
                print(tr('binary_ready'), flush=True)
            self.write_state(domain, 'binary_ready', expected)
            self.stage = tr('installing_caddy')
            print(tr('caddy_progress'), flush=True)
            key = work / 'caddy.key'
            self.run(['curl', '--proto', '=https', '--proto-redir', '=https', '--tlsv1.2', '-fLsS', '--retry', '3', '--max-time', '60',
                      'https://dl.cloudsmith.io/public/caddy/stable/gpg.key', '-o', key])
            try:
                key_verifier.verify(key, runner=lambda command, **options: self.run(
                    command, capture=True, timeout=options["timeout"]))
            except (ValueError, subprocess.SubprocessError) as error:
                raise SetupError(tr('caddy_key_failed')) from error
            keyring = work / 'caddy.gpg'
            self.run(['gpg', '--batch', '--yes', '--dearmor', '--output', keyring, key])
            destination = self.path('/usr/share/keyrings/caddy-stable-archive-keyring.gpg')
            shutil.copyfile(keyring, destination)
            destination.chmod(0o644)
            source = self.path('/etc/apt/sources.list.d/caddy-stable.list')
            source.write_text('deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] '
                              'https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main\n')
            source.chmod(0o644)
            self.apt('update')
            version = self.metadata()['caddy_version']
            self.apt('install', '-y', 'caddy=' + version)
            self.run(['apt-mark', 'hold', 'caddy'])
            self.run(['sh', self.kit / 'bin/require-pq-caddy'])
            self.stage = tr('installing_relay')
            print(tr('relay_progress'), flush=True)
            self.run(['sh', self.kit / 'scripts/install.sh', '--binary', staged, '--sha256', expected, '--no-start'])
            self.run(['systemctl', 'enable', '--now', *UNITS])
            self.run(['systemctl', 'start', 'strfry-prune.service'])
            self.run(['systemctl', 'enable', '--now', 'caddy'])
            self.configure_caddy(domain, work)
            self.write_state(domain, 'services_installed', expected)
        self.stage = tr('checking_https')
        print(tr('https_progress'), flush=True)
        self.check(domain, tls_timeout)
        self.write_state(domain, 'complete', expected)

    def check(self, domain, tls_timeout):
        self.run(['systemctl', 'is-active', 'caddy', *UNITS])
        self.run([self.path('/usr/local/libexec/strfry-health')])
        deadline = time.monotonic() + tls_timeout
        last_error = ''
        while True:
            # Verify this VPS's listener and certificate, even with NAT or split DNS.
            base = ['curl', '--noproxy', '*', '--resolve', f'{domain}:443:127.0.0.1',
                    '--connect-timeout', '3', '--max-time', '5', '-sS']
            info = self.run([*base, '--fail', '-H', 'Accept: application/nostr+json',
                             f'https://{domain}/relay'], capture=True, check=False, timeout=10)
            if info.returncode == 0:
                try:
                    data = json.loads(info.stdout)
                    valid = data['limitation']['max_subscriptions'] == 20 and 40 in data['supported_nips']
                except (ValueError, KeyError, TypeError):
                    valid = False
                if not valid:
                    raise SetupError(tr('nip11_mismatch'))
                metrics = self.run([*base, '-o', '/dev/null', '-w', '%{http_code}',
                                    f'https://{domain}/metrics'], capture=True, timeout=10)
                if metrics.stdout.strip() != '404':
                    raise SetupError(tr('metrics_exposed'))
                print(tr('ready', v0=domain, v1=domain), flush=True)
                return
            last_error = info.stderr.strip()
            if time.monotonic() >= deadline:
                raise SetupError(tr('https_not_ready') + last_error)
            print(tr('waiting_certificate'), flush=True)
            time.sleep(min(5, max(0, deadline - time.monotonic())))


def parser():
    result = argparse.ArgumentParser(description=tr('description'), add_help=False)
    result._optionals.title = tr('options_title')
    result.add_argument('-h', '--help', action='help', help=tr('help_help'))
    result.add_argument('--lang', choices=('en', 'ru', 'de'), help=tr('language_help'))
    result.add_argument('--domain', help=tr('domain_help'))
    result.add_argument('--mode', choices=('binary', 'source'), help=tr('mode_help'))
    result.add_argument('--binary', help=tr('binary_help'))
    result.add_argument('--sha256', help=tr('checksum_help'))
    result.add_argument('--plan', action='store_true', help=tr('plan_help'))
    result.add_argument('--yes', action='store_true', help=tr('yes_help'))
    result.add_argument('--check', action='store_true', help=tr('check_help'))
    result.add_argument('--tls-timeout', type=int, default=180, help=tr('timeout_help'))
    return result


def main(argv=None):
    setup = Setup()
    try:
        choose_language(list(sys.argv[1:] if argv is None else argv))
        setup.stage = tr('preparation')
        args = parser().parse_args(argv)
        if not 1 <= args.tls_timeout <= 600:
            raise SetupError(tr('invalid_timeout'))
        if args.check:
            if args.plan or args.mode or args.binary or args.sha256 or args.yes:
                raise SetupError(tr('check_conflict'))
            domain = args.domain
            if not domain:
                domain = json.loads(setup.path('/var/lib/neighbors-relay-setup/state.json').read_text())['domain']
            setup.check(domain_name(domain), args.tls_timeout)
            return 0
        interactive = sys.stdin.isatty()
        domain = args.domain
        if not domain and interactive:
            domain = input(tr('domain_prompt'))
        if not domain:
            raise SetupError(tr('domain_required'))
        domain = domain_name(domain)
        mode = args.mode
        if not mode and interactive and not args.yes:
            choice = input(tr('method_prompt')).strip()
            if choice not in ('', '1', '2'):
                raise SetupError(tr('invalid_method'))
            mode = 'source' if choice == '2' else 'binary'
        mode = mode or 'binary'
        if mode == 'source' and (args.binary or args.sha256):
            raise SetupError(tr('source_binary_conflict'))
        binary, expected = setup.candidate(args.binary, args.sha256) if mode == 'binary' else (None, None)
        addresses = setup.preflight(mode, domain)
        setup.plan(mode, domain, addresses, binary)
        if args.plan:
            return 0
        if not args.yes:
            if not interactive:
                raise SetupError(tr('confirmation_required'))
            if input(tr('confirm')).strip().lower() not in ('да', 'yes', 'ja'):
                print(tr('cancelled'))
                return 0
        # Serialize installations. Locking does not depend on a user-controlled repository path.
        with setup.path('/run/lock/neighbors-relay-setup.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise SetupError(tr('already_running')) from error
            setup.preflight(mode, domain)  # Recheck after confirmation and lock acquisition.
            setup.install(mode, domain, binary, expected, args.tls_timeout)
        return 0
    except (SetupError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(tr('stopped', v0=setup.stage, v1=error), file=sys.stderr)
        if not setup.started:
            print(tr('no_changes'), file=sys.stderr)
            return 1
        print(tr('recovery'), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print(tr('interrupted'), file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
