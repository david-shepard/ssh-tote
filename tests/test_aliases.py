import os
import shutil
import tempfile
import unittest
from pathlib import Path

from sshtotelib.aliases import alias_items, capture_aliases, parse_alias_listing

ZSH_LISTING = r"""
alias -- -='cd -'
alias -g ...=../..
alias -s txt=vim
alias '!x'=ls
alias ll='ls -l'
alias g=git
alias nl=$'echo a\n  echo b'
alias which-command=whence
"""
BASH_LISTING = (
    "alias ..='cd ..'\nalias multi='echo one\necho two'\nalias q='echo '\\''hi'\\'''\n"
)


class ParseAliasListingTest(unittest.TestCase):
    def test_zsh_listing_keeps_only_bash_compatible_aliases(self):
        expected = {
            "ll": "ls -l",
            "g": "git",
            "nl": "echo a\n  echo b",
            "which-command": "whence",
        }
        self.assertEqual(parse_alias_listing(ZSH_LISTING), expected)

    def test_bash_listing(self):
        expected = {"..": "cd ..", "multi": "echo one\necho two", "q": "echo 'hi'"}
        self.assertEqual(parse_alias_listing(BASH_LISTING), expected)


class AliasItemsTest(unittest.TestCase):
    ALIASES = {"ll": "ls -l", "gco": "git checkout", "which-command": "whence"}

    def test_remote_unsafe_aliases_are_not_offered(self):
        names = [item.name for item in alias_items(self.ALIASES)]
        self.assertEqual(names, ["gco", "ll"])


class CaptureAliasesTest(unittest.TestCase):
    RC_FILES = {"bash": ".bashrc", "zsh": ".zshrc"}

    def test_reads_aliases_and_function_names_from_the_rc_file(self):
        for shell, rc_file in self.RC_FILES.items():
            path = shutil.which(shell)
            if not path:
                continue
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as home:
                Path(home, rc_file).write_text(
                    "my_func() { :; }\nalias history=my_func\n"
                )
                environ = {"HOME": home, "PATH": os.environ["PATH"]}
                aliases, functions = capture_aliases(path, environ)
                self.assertEqual(aliases["history"], "my_func")
                self.assertIn("my_func", functions)
