"""Runs the real bootstrap locally, through each login shell ssh might hit."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from sshtotelib.items import Item, Kind
from sshtotelib.session import Session

LOGIN_SHELLS = ("sh", "bash", "zsh", "dash", "fish", "tcsh")
TRICKY_VALUE = 'it\'s "quoted" $NOT_EXPANDED'
REPORT = (
    'hello; echo "T=$SSH_TOTE_TEST"; echo "P=$SSH_TOTE_PATHY";'
    ' echo "O=${SSH_TOTE_OFF-unset}"'
)


class RemoteSessionTestCase(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.tmpdir = os.path.join(self.home, "tmp with space")
        os.makedirs(self.tmpdir)
        self.items = [
            Item(Kind.ENV, "SSH_TOTE_TEST", TRICKY_VALUE),
            Item(Kind.ENV, "SSH_TOTE_PATHY", self.home + "/bin"),
            Item(Kind.ENV, "SSH_TOTE_OFF", "nope", selected=False),
            Item(Kind.ALIAS, "hello", "echo hello-from-alias"),
        ]

    def run_remote(self, login_shell, command, dotfiles_dir=None):
        session = Session(self.items, self.home, dotfiles_dir, command)
        environ = {
            "HOME": self.home,
            "PATH": os.environ["PATH"],
            "TMPDIR": self.tmpdir,
            "TERM": "dumb",
        }
        return subprocess.run(
            [login_shell, "-c", session.bootstrap().command],
            env=environ,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )


class LoginShellTest(RemoteSessionTestCase):
    def test_every_installed_login_shell_gets_env_and_aliases(self):
        expected = [
            "hello-from-alias",
            f"T={TRICKY_VALUE}",
            f"P={self.home}/bin",
            "O=unset",
        ]
        for shell in LOGIN_SHELLS:
            path = shutil.which(shell)
            if path:
                with self.subTest(shell=shell):
                    output = self.run_remote(path, REPORT).stdout.splitlines()
                    self.assertEqual(output[-len(expected) :], expected)

    def test_temp_dir_is_removed_after_logout(self):
        self.run_remote("/bin/sh", "true")
        self.assertEqual(os.listdir(self.tmpdir), [])

    def test_remote_exit_status_is_returned(self):
        self.assertEqual(self.run_remote("/bin/sh", "exit 3").returncode, 3)

    def test_payload_is_not_left_in_the_process_list(self):
        processes = self.run_remote("bash", "ps -A -o args=").stdout.splitlines()
        bootstraps = [args for args in processes if args.startswith("sh -c d=")]
        self.assertEqual(bootstraps, [])


class DotfilesDirTest(RemoteSessionTestCase):
    def setUp(self):
        super().setUp()
        self.dotfiles = Path(self.home, "dots")
        (self.dotfiles / "bin").mkdir(parents=True)
        (self.dotfiles / ".git").mkdir()
        (self.dotfiles / ".bashrc").write_text("export FROM_DIR=yes\n")
        tool = self.dotfiles / "bin" / "dottool"
        tool.write_text("#!/bin/sh\necho dottool-ran\n")
        tool.chmod(0o755)

    def test_bin_is_on_path_bashrc_is_sourced_and_git_is_skipped(self):
        command = 'dottool; echo "D=$FROM_DIR"; ls -A "$SSHHOME"'
        output = self.run_remote("/bin/sh", command, self.dotfiles).stdout.splitlines()
        self.assertEqual(output[-4:], ["dottool-ran", "D=yes", ".bashrc", "bin"])

    def test_symlinks_dont_reach_the_server(self):
        (self.dotfiles / "link").symlink_to(".bashrc")
        command = 'ls -A "$SSHHOME"'
        output = self.run_remote("/bin/sh", command, self.dotfiles).stdout.splitlines()
        self.assertEqual(output[-2:], [".bashrc", "bin"])

    def test_hard_links_unpack_as_regular_files(self):
        (self.dotfiles / "copy").hardlink_to(self.dotfiles / ".bashrc")
        command = 'cat "$SSHHOME/copy"'
        output = self.run_remote("/bin/sh", command, self.dotfiles).stdout.splitlines()
        self.assertEqual(output[-1:], ["export FROM_DIR=yes"])
