#!/usr/bin/env python3
import ast
import importlib.util
import io
import json
import os
from pathlib import Path
import string
import subprocess
import tempfile
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_languages', KIT / 'scripts/setup-relay.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Languages(unittest.TestCase):
    def test_empty_or_missing_config_language_preserves_system_locale(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'install.conf'
            for contents in ('AUTH=yes\n', 'AUTH=yes\nLANGUAGE=\n', 'LANGUAGE="  "\n'):
                config.write_text(contents)
                for locale, expected in [('ru_RU.UTF-8', 'ru'), ('de_DE.UTF-8', 'de'), ('C.UTF-8', 'en')]:
                    with self.subTest(contents=contents, locale=locale), patch.dict(os.environ, {'LC_ALL': locale}, clear=True):
                        module.choose_language(['--config', str(config), '--yes'])
                        self.assertEqual(module.LANGUAGE, expected)

    def test_config_language_is_case_insensitive_and_cli_takes_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'install.conf'
            for configured, expected in [('RU', 'ru'), ('De', 'de'), ('en', 'en')]:
                config.write_text('LANGUAGE=' + configured + '\n')
                with self.subTest(configured=configured), patch.dict(os.environ, {'LC_ALL': 'de_DE.UTF-8'}, clear=True):
                    module.choose_language(['--config', str(config), '--yes'])
                    self.assertEqual(module.LANGUAGE, expected)
                    module.choose_language(['--config', str(config), '--lang', 'ru', '--yes'])
                    self.assertEqual(module.LANGUAGE, 'ru')

    def test_empty_config_language_follows_locale_environment_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'install.conf'
            config.write_text('LANGUAGE=\n')
            cases = [
                ({'LC_ALL': 'ru_RU.UTF-8', 'LC_MESSAGES': 'de_DE.UTF-8', 'LANG': 'en_US.UTF-8'}, 'ru'),
                ({'LC_ALL': '', 'LC_MESSAGES': 'de_DE.UTF-8', 'LANG': 'ru_RU.UTF-8'}, 'de'),
                ({'LC_ALL': '', 'LC_MESSAGES': '', 'LANG': 'ru_RU.UTF-8'}, 'ru'),
                ({'LC_ALL': 'fr_FR.UTF-8', 'LANG': 'ru_RU.UTF-8'}, 'en'),
                ({}, 'en'),
            ]
            for environment, expected in cases:
                with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True):
                    module.choose_language(['--config', str(config), '--yes'])
                    self.assertEqual(module.LANGUAGE, expected)

    def test_catalogs_cover_every_message_and_preserve_placeholders(self):
        catalogs = module.CATALOGS
        used = {n.args[0].value for n in ast.walk(ast.parse((KIT / 'scripts/setup-relay.py').read_text()))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'tr'}
        self.assertEqual(used, set(catalogs['ru']))
        for lang, catalog in catalogs.items():
            self.assertEqual(set(catalog), used)
            for key, text in catalog.items():
                fields = lambda value: {f for _, f, _, _ in string.Formatter().parse(value) if f is not None}
                self.assertEqual(fields(text), fields(catalogs['ru'][key]), (lang, key))
                self.assertTrue(text.strip())
                if lang != 'ru':
                    self.assertFalse(any('\u0400' <= c <= '\u04ff' for c in text), (lang, key))

    def test_explicit_language_overrides_locale_and_help_is_read_only(self):
        for lang, word in [('en', 'wizard language'), ('de', 'Sprache des Assistenten'), ('ru', 'язык мастера')]:
            result = subprocess.run(['sh', 'setup.sh', '--lang', lang, '--help'], cwd=KIT,
                                    env=dict(os.environ, LC_ALL='ru_RU.UTF-8'), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(word, result.stdout)

    def test_locale_and_interactive_selection(self):
        with patch.dict(os.environ, {'LC_ALL': 'de_DE.UTF-8'}):
            module.choose_language(['--plan'])
            self.assertEqual(module.LANGUAGE, 'de')
            with patch.object(module.sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='ru'):
                module.choose_language([])
                self.assertEqual(module.LANGUAGE, 'ru')
            module.choose_language(['--lang', 'en'])
            self.assertEqual(module.LANGUAGE, 'en')


if __name__ == '__main__':
    unittest.main()
