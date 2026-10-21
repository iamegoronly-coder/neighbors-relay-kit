#!/usr/bin/env python3
"""Documentation stays consistent with the release manifest and relay configuration.

Checks every relative Markdown link and heading anchor, the six install commands that must
name the same candidate and checksum, and the retention numbers quoted in the READMEs.
"""
import json
import re
import unicodedata
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
INSTALL_DOCS = ['README.md', 'README.ru.md', 'README.de.md',
                'docs/quickstart.md', 'docs/quickstart.ru.md', 'docs/quickstart.de.md']
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
HEADING = re.compile(r'^#{1,6}\s+(.*?)\s*#*\s*$', re.M)
FENCE = re.compile(r'```.*?```', re.S)


def slug(heading):
    text = re.sub(r'`([^`]*)`', r'\1', heading)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = unicodedata.normalize('NFC', text).lower()
    text = ''.join(ch for ch in text if ch.isalnum() or ch in ' -_')
    return text.replace(' ', '-')


def markdown_files():
    return sorted([*KIT.glob('*.md'), *KIT.glob('docs/*.md')])


class LinkTests(unittest.TestCase):
    def test_relative_links_and_anchors_resolve(self):
        for source in markdown_files():
            text = FENCE.sub('', source.read_text())
            for target in LINK.findall(text):
                if target.startswith(('http://', 'https://', 'mailto:')):
                    continue
                path, _, anchor = target.partition('#')
                resolved = (source.parent / path).resolve() if path else source
                with self.subTest(source=source.name, link=target):
                    self.assertTrue(resolved.exists(), f'{target} does not exist')
                    if anchor:
                        headings = {slug(h) for h in HEADING.findall(FENCE.sub('', resolved.read_text()))}
                        self.assertIn(anchor, headings, f'no heading for #{anchor} in {resolved.name}')


class CandidateReferenceTests(unittest.TestCase):
    def setUp(self):
        self.version = json.loads((KIT / 'release/local-candidate.json').read_text())['version']
        number = re.fullmatch(r'v\d+\.\d+\.\d+-test\.(\d+)', self.version)
        self.assertIsNotNone(number, 'manifest version must look like v0.1.0-test.N')
        self.placeholder = f'COPY_SHA256_FROM_TEST_{number.group(1)}_RELEASE_NOTES'

    def test_install_commands_name_the_manifest_candidate(self):
        archive = f'neighbors-relay-{self.version}.tar.gz'
        for name in INSTALL_DOCS:
            text = (KIT / name).read_text()
            with self.subTest(doc=name):
                self.assertIn(f'/releases/download/{self.version}/{archive}', text)
                self.assertIn(f'git clone --branch {self.version} --single-branch', text)
                stale = {m for m in re.findall(r'v\d+\.\d+\.\d+-test\.\d+', text)} - {self.version}
                self.assertFalse(stale, f'other candidate versions mentioned: {sorted(stale)}')

    def test_pinned_checksum_is_shared_and_matches_the_archive(self):
        pins = {}
        for name in INSTALL_DOCS:
            found = re.findall(r"printf '%s  %s\\n' '([0-9a-f]{64}|COPY_SHA256_FROM_TEST_\d+_RELEASE_NOTES)'", (KIT / name).read_text())
            self.assertEqual(len(found), 1, f'{name} must pin exactly one archive checksum')
            pins[name] = found[0]
        values = set(pins.values())
        self.assertEqual(len(values), 1, f'install docs disagree on the checksum: {pins}')
        value = values.pop()
        checksum = KIT / 'out' / f'neighbors-relay-{self.version}.tar.gz.sha256'
        if value == self.placeholder:
            return  # the source tag and bundled docs carry the placeholder by design
        self.assertRegex(value, r'^[0-9a-f]{64}$')
        if checksum.exists():
            self.assertEqual(value, checksum.read_text().split()[0], 'pinned checksum differs from the packaged archive')


class RetentionTests(unittest.TestCase):
    def test_readmes_and_units_quote_the_configured_retention(self):
        config = (KIT / 'config/strfry.conf').read_text()
        seconds = int(re.search(r'^\s*rejectEventsOlderThanSeconds = (\d+)$', config, re.M).group(1))
        self.assertEqual(seconds % 3600, 0)
        hours = seconds // 3600
        self.assertIn(f'Normal events: {hours}h by created_at', config)
        self.assertIn(f'older than {hours} hours', (KIT / 'systemd/strfry-prune.service').read_text())
        self.assertIn(f'{hours}-hour history', (KIT / 'systemd/strfry-prune.timer').read_text())
        for name, phrase in [('README.md', f'at most {hours} h old'), ('README.ru.md', f'не старше {hours} ч'),
                             ('README.de.md', f'höchstens {hours} Stunden alt')]:
            with self.subTest(doc=name):
                text = (KIT / name).read_text()
                self.assertIn(phrase, text)
                self.assertIn(f'delete --age {seconds}', text)


if __name__ == '__main__':
    unittest.main()
