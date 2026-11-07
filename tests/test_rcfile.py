import os
import shutil
import subprocess
import tempfile
import unittest

from sshtotelib.items import Item, Kind
from sshtotelib.rcfile import alias_section, quote_with_remote_home

HOME = "/h"
SHELLS = ("sh", "bash", "dash", "zsh")


class QuoteWithRemoteHomeTest(unittest.TestCase):
    def test_path_under_home(self):
        self.assertEqual(
            quote_with_remote_home("/h/.kube/config", HOME), '"$HOME"/.kube/config'
        )

    def test_home_itself(self):
        self.assertEqual(quote_with_remote_home("/h", HOME), '"$HOME"')

    def test_colon_separated_list(self):
        quoted = quote_with_remote_home("/h/a b:/opt:/h", HOME)
        self.assertEqual(quoted, '"$HOME"\'/a b\':/opt:"$HOME"')

    def test_similar_prefix_is_not_home(self):
        self.assertEqual(quote_with_remote_home("/home2/x", HOME), "/home2/x")

    def test_root_home_is_never_rewritten(self):
        self.assertEqual(quote_with_remote_home("/etc", "/"), "/etc")

    def test_quotes_are_escaped(self):
        self.assertEqual(quote_with_remote_home("it's", HOME), "'it'\"'\"'s'")


class AliasSectionTest(unittest.TestCase):
    HOSTILE_NAMES = (
        "x;touch injected;y",
        "x$(touch injected)y",
        "x`touch injected`y",
        "x\ntouch injected\ny",
        "x>injected",
    )

    def test_alias_names_cannot_run_commands(self):
        installed = [shell for shell in SHELLS if shutil.which(shell)]
        for shell in installed:
            for name in self.HOSTILE_NAMES:
                with self.subTest(shell=shell, name=name):
                    section = alias_section([Item(Kind.ALIAS, name, "true")])
                    with tempfile.TemporaryDirectory() as directory:
                        subprocess.run(
                            [shell, "-c", section],
                            cwd=directory,
                            capture_output=True,
                            timeout=30,
                        )
                        self.assertEqual(os.listdir(directory), [])

    def test_simple_alias_stays_readable(self):
        section = alias_section([Item(Kind.ALIAS, "g", "git")])
        self.assertIn("alias g=git\n", section)
