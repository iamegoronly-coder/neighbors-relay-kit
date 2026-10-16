#!/usr/bin/env python3
import ast
import importlib.util
import io
import json
import os
from pathlib import Path
import string
import subprocess
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_languages', KIT / 'scripts/setup-relay.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Languages(unittest.TestCase):
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
