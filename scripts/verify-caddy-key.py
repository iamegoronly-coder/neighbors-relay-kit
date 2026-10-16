#!/usr/bin/env python3
"""Verify the Caddy stable APT primary key before trusting any downloaded keyring."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import time

# Reviewed against the official stable repository's public key metadata, 2026-10-16.
# https://cloudsmith.io/~caddy/repos/stable/packages/
FINGERPRINT = '65760C51EDEA2017CEA2CA15155B6D79CA56EA34'


def validate_listing(listing, now=None):
    now = time.time() if now is None else now
    primaries, fingerprints = [], []
    waiting = False
    for line in listing.splitlines():
        fields = line.split(':')
        if fields[0] == 'pub':
            if len(fields) < 12 or waiting:
                raise ValueError('Malformed Caddy primary key metadata.')
            primaries.append(fields)
            waiting = True
        elif fields[0] == 'sub':
            if waiting:
                raise ValueError('Missing primary key fingerprint.')
        elif fields[0] == 'fpr' and waiting:
            if len(fields) <= 9:
                raise ValueError('Malformed Caddy fingerprint.')
            fingerprints.append(fields[9].upper())
            waiting = False
    if waiting or len(primaries) != 1 or fingerprints != [FINGERPRINT]:
        raise ValueError('Caddy key fingerprint mismatch: expected exactly one primary key ' + FINGERPRINT)
    key = primaries[0]
    if key[1] in ('r', 'e', 'd') or 'D' in key[11]:
        raise ValueError('Caddy primary key is revoked, expired or disabled.')
    if key[6] and (not key[6].isdigit() or int(key[6]) <= now):
        raise ValueError('Caddy primary key has expired or has an invalid expiry.')
    return FINGERPRINT


def verify(path, runner=None):
    run = runner or subprocess.run
    # No user keyring, gpg.conf, keyserver or trust database is used.
    with tempfile.TemporaryDirectory(prefix='neighbors-caddy-gpg-') as home:
        result = run(['gpg', '--no-options', '--homedir', home, '--batch', '--no-tty',
                      '--with-colons', '--fingerprint', '--show-keys', str(Path(path).resolve())],
                     text=True, capture_output=True, check=True, timeout=30)
    return validate_listing(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('key', type=Path)
    args = parser.parse_args()
    try:
        print('PASS Caddy primary key: ' + verify(args.key))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f'verify-caddy-key: {error}\n')


if __name__ == '__main__':
    main()
