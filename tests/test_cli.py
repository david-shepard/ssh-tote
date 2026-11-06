import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from sshtotelib.cli import EXIT_USAGE, Paths, main


def run_main(argv, environ):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = main(argv, environ)
    return exit_code, stdout.getvalue(), stderr.getvalue()


class MainTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.environ = {
            "HOME": directory.name,
            "XDG_CONFIG_HOME": directory.name,
            "SHELL": "/bin/false",
            "EDITOR": "vim",
        }

    def test_dry_run_sends_only_variables_listed_in_env(self):
        _, stdout, _ = run_main(["--print", "--no-aliases", "box"], self.environ)
        self.assertNotIn("EDITOR", stdout)
        config = Path(self.environ["XDG_CONFIG_HOME"], "ssh-tote", "config.toml")
        config.parent.mkdir()
        config.write_text('env = ["EDITOR"]\n')
        _, stdout, _ = run_main(["--print", "--no-aliases", "box"], self.environ)
        self.assertIn("export EDITOR=vim\n", stdout)

    def test_missing_dotfiles_dir_is_a_usage_error(self):
        exit_code, _, _ = run_main(
            ["--print", "--dir", "/nonexistent", "box"], self.environ
        )
        self.assertEqual(exit_code, EXIT_USAGE)

    def test_config_paths_are_absolute_even_with_a_relative_config_home(self):
        paths = Paths.from_environment({"XDG_CONFIG_HOME": "relative"})
        self.assertTrue(paths.settings.is_absolute())
        self.assertEqual(paths.settings.name, "config.toml")

    def test_unsupported_shell_warns_and_continues(self):
        _, _, stderr = run_main(["--print", "box"], self.environ)
        self.assertIn("can't read aliases from false", stderr)
