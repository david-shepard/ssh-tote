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

    def test_names_no_shell_could_define_are_dropped(self):
        unportable = [
            "x;touch>injected;y",
            "x|y",
            "x&y",
            "x(y",
            "x)y",
            "x<y",
            "x>y",
            "x\x1by",
            "x\n",
        ]
        for name in unportable:
            with self.subTest(name=name):
                self.assertEqual(parse_alias_listing(f"alias '{name}'=true\n"), {})

    def test_unusual_but_valid_names_are_kept(self):
        # oh-my-zsh defines `gc!`, `1` and `...`; `?` is a popular shortcut.
        for name in ("gc!", "g+", "?", "...", "_", "1", "git-svn", "a:b", "@x", "ñ"):
            with self.subTest(name=name):
                listing = f"alias '{name}'=true\n"
                self.assertEqual(parse_alias_listing(listing), {name: "true"})


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

    def test_real_shell_listing_keeps_valid_names_and_drops_hostile_ones(self):
        for shell, rc_file in self.RC_FILES.items():
            path = shutil.which(shell)
            if not path:
                continue
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as home:
                Path(home, rc_file).write_text(
                    "alias 'x;touch>injected;y=true'\nalias 'gc!=git commit'\n"
                )
                environ = {"HOME": home, "PATH": os.environ["PATH"]}
                aliases, _ = capture_aliases(path, environ)
                self.assertEqual(aliases.get("gc!"), "git commit")
                self.assertNotIn("x;touch>injected;y", aliases)
