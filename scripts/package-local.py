#!/usr/bin/env python3
"""Create a private, self-contained deployment bundle. Never uploads or publishes anything."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import tempfile

KIT = Path(__file__).resolve().parents[1]
ASSETS = {'strfry', 'source.tar.gz', 'build-info.txt', 'packages.lock', 'strfry-neighbors.patch', 'COPYING'}
TOP_LEVEL = {'README.md', 'README.ru.md', 'README.de.md', 'LICENSE', 'LICENSES', 'SECURITY.md', 'SECURITY.ru.md', 'SECURITY.de.md', 'setup.sh',
             '.gitignore', '.dockerignore', 'bin', 'build', 'config', 'docs', 'patch', 'release',
             'scripts', 'systemd', 'tests'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def package(kit, candidate, output):
    kit, candidate, output = Path(kit), Path(candidate), Path(output)
    checksum_path = Path(str(output) + '.sha256')
    if output.exists() or checksum_path.exists():
        raise ValueError('Output already exists; choose a new filename.')
    metadata = json.loads((kit / 'release/local-candidate.json').read_text())
    if sha(candidate / 'strfry') != metadata['sha256']:
        raise ValueError('Candidate binary does not match the reviewed local manifest.')
    if sha(kit / 'patch/strfry-neighbors.patch') != metadata['patch_sha256']:
        raise ValueError('Kit patch differs from the reviewed candidate.')
    if (candidate / 'strfry-neighbors.patch').read_bytes() != (kit / 'patch/strfry-neighbors.patch').read_bytes():
        raise ValueError('Candidate and kit patches differ.')
    if (candidate / 'packages.lock').read_bytes() != (kit / 'build/packages.lock').read_bytes():
        raise ValueError('Candidate and kit toolchain locks differ.')
    records = {}
    for line in (candidate / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if name not in ASSETS or name in records:
            raise ValueError('Unexpected or duplicate candidate manifest entry.')
        if sha(candidate / name) != expected:
            raise ValueError('Corrupt candidate asset: ' + name)
        records[name] = expected
    if records.keys() != ASSETS:
        raise ValueError('Incomplete candidate source/license manifest.')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.neighbors-bundle-', dir=output.parent)
    os.close(fd)
    try:
        with tarfile.open(temporary, 'w:gz') as archive:
            for entry in sorted(TOP_LEVEL):
                path = kit / entry
                if not path.exists():
                    raise ValueError('Missing kit entry: ' + entry)
                paths = [path, *sorted(path.rglob('*'))] if path.is_dir() else [path]
                for item in paths:
                    if '__pycache__' in item.parts or item.suffix == '.pyc' or item.name == '.DS_Store':
                        continue
                    if item.is_symlink():
                        raise ValueError('Symlinks are not accepted in a local deployment kit.')
                    archive.add(item, arcname='neighbors-relay/' + item.relative_to(kit).as_posix(), recursive=False)
            for name in sorted(ASSETS | {'SHA256SUMS'}):
                if (candidate / name).is_symlink():
                    raise ValueError('Symlink in candidate assets.')
                archive.add(candidate / name, arcname='neighbors-relay/payload/' + name, recursive=False)
        # Exclusive creation: never overwrite another bundle after a concurrent check/create race.
        os.link(temporary, output)
        with checksum_path.open('x') as stream:
            stream.write(sha(output) + '  ' + output.name + '\n')
    finally:
        os.unlink(temporary)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        candidate = args.candidate or KIT / 'out' / json.loads((KIT / 'release/local-candidate.json').read_text())['version']
        output = package(KIT, candidate, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'package-local: {error}\n')
    print(f'Local bundle: {output}\nChecksum: {output}.sha256\nNothing was published.')


if __name__ == '__main__':
    main()
