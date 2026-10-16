#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package_local', KIT / 'scripts/package-local.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.kit, self.candidate = self.root / 'kit', self.root / 'candidate'
        shutil.copytree(KIT, self.kit, ignore=shutil.ignore_patterns('out', '__pycache__', '*.pyc', '.git'))
        self.candidate.mkdir()
        for name in module.ASSETS:
            (self.candidate / name).write_bytes(('test ' + name).encode())
        for name, rel in [('strfry-neighbors.patch', 'patch/strfry-neighbors.patch'), ('packages.lock', 'build/packages.lock')]:
            shutil.copyfile(self.kit / rel, self.candidate / name)
        metadata = json.loads((self.kit / 'release/local-candidate.json').read_text())
        metadata['sha256'] = module.sha(self.candidate / 'strfry')
        (self.kit / 'release/local-candidate.json').write_text(json.dumps(metadata))
        self.manifest()
        self.output = self.root / 'bundle.tar.gz'

    def manifest(self):
        (self.candidate / 'SHA256SUMS').write_text(''.join(module.sha(self.candidate / name) + '  ' + name + '\n' for name in sorted(module.ASSETS)))

    def test_bundle_contains_sources_and_no_private_extras(self):
        (self.kit / '.env').write_text('private fixture')
        (self.kit / 'out').mkdir()
        (self.kit / 'out/private').write_text('private fixture')
        module.package(self.kit, self.candidate, self.output)
        with tarfile.open(self.output) as archive:
            names = set(archive.getnames())
            for name in ('setup.sh', 'payload/strfry', 'payload/source.tar.gz', 'payload/COPYING', 'scripts/setup-relay.py',
                         'scripts/verify-caddy-key.py', 'scripts/locales/en.json',
                         'scripts/locales/ru.json', 'scripts/locales/de.json',
                         'README.de.md', 'SECURITY.de.md', 'SECURITY.ru.md', 'docs/caddy.de.md'):
                self.assertIn('neighbors-relay/' + name, names)
            self.assertFalse(any('/out/' in name or name.endswith('/.env') for name in names))
        self.assertTrue(Path(str(self.output) + '.sha256').read_text().startswith(module.sha(self.output)))

    def test_corruption_and_missing_source_refused(self):
        for name in ('strfry', 'source.tar.gz'):
            with self.subTest(name=name):
                data = (self.candidate / name).read_bytes()
                (self.candidate / name).write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    module.package(self.kit, self.candidate, self.output)
                self.assertFalse(self.output.exists())
                (self.candidate / name).write_bytes(data)
        (self.candidate / 'SHA256SUMS').write_text(module.sha(self.candidate / 'strfry') + '  strfry\n')
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            module.package(self.kit, self.candidate, self.output)

    def test_path_traversal_in_manifest_refused(self):
        with (self.candidate / 'SHA256SUMS').open('a') as stream:
            stream.write('0' * 64 + '  ../private\n')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            module.package(self.kit, self.candidate, self.output)

    def test_existing_output_never_overwritten(self):
        self.output.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            module.package(self.kit, self.candidate, self.output)
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_symlink_not_packaged(self):
        secret = self.root / 'secret'
        secret.write_text('private')
        (self.kit / 'docs/link').symlink_to(secret)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            module.package(self.kit, self.candidate, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
