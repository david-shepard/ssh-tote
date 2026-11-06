import tempfile
import unittest
from pathlib import Path

from sshtotelib.settings import Settings, SettingsError, SettingsFile


class SettingsFileTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.file = SettingsFile(Path(directory.name) / "ssh-tote" / "config.toml")

    def test_missing_file_gives_defaults(self):
        self.assertEqual(self.file.load(), Settings())

    def test_save_then_load_round_trips(self):
        settings = Settings(
            dotfiles_dir="~/dots", env={"A_*", "!A_S", "T"}, aliases={"g*", "ll"}
        )
        self.file.save(settings)
        self.assertEqual(self.file.load(), settings)

    def test_invalid_toml_is_reported(self):
        self.file.path.parent.mkdir(parents=True)
        self.file.path.write_text("env = [")
        with self.assertRaises(SettingsError):
            self.file.load()

    def test_wrong_types_are_reported(self):
        self.file.path.parent.mkdir(parents=True)
        for text in ('env = "AWS_*"', "include_env = [1]", "dir = 5"):
            with self.subTest(text=text):
                self.file.path.write_text(text)
                with self.assertRaises(SettingsError):
                    self.file.load()

    def test_old_keys_warn_and_include_env_becomes_env(self):
        self.file.path.parent.mkdir(parents=True)
        self.file.path.write_text(
            'env = ["EDITOR"]\ninclude_env = ["GH_TOKEN"]\nexclude_env = ["AWS_*"]\n'
        )
        warnings = []
        settings = self.file.load(warn=warnings.append)
        self.assertEqual(settings.env, {"EDITOR", "GH_TOKEN"})
        self.assertEqual(len(warnings), 2)

    def test_exclude_aliases_warns_and_is_ignored(self):
        self.file.path.parent.mkdir(parents=True)
        self.file.path.write_text('exclude_aliases = ["g*"]\n')
        warnings = []
        settings = self.file.load(warn=warnings.append)
        self.assertEqual(settings, Settings())
        self.assertEqual(len(warnings), 1)
        self.assertIn("`aliases`", warnings[0])
