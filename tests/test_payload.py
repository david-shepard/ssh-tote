import base64
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from sshtotelib.bootstrap import MAX_BOOTSTRAP_BYTES, Bootstrap
from sshtotelib.payload import DOTFILES_NAME, Payload

FILE_BYTES = 100_000
FILE_COUNT = 20
SECRET = b"contents of a file outside the dotfiles dir"


class PayloadTest(unittest.TestCase):
    def test_huge_dotfiles_dir_stops_early_but_is_still_too_large(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(FILE_COUNT):
                Path(directory, f"f{index:02}").write_bytes(os.urandom(FILE_BYTES))
            encoded = Payload("", Path(directory)).encode()
        self.assertTrue(Bootstrap.for_payload(encoded).too_large)
        # Random bytes don't compress, so reading every file would be ~2.7 MB.
        self.assertLess(len(encoded), 4 * MAX_BOOTSTRAP_BYTES)


class SymlinkTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.dots = self.root / "dots"
        self.dots.mkdir()
        (self.dots / "kept").write_text("kept\n")
        self.outside = self.root / "outside"
        self.outside.mkdir()
        (self.outside / "key").write_bytes(SECRET)

    def encode(self):
        """Encode the dir; return (archive member names, file bytes, warnings)."""
        warnings = []
        encoded = Payload("", self.dots).encode(warn=warnings.append)
        prefix = f"{DOTFILES_NAME}/"
        with tarfile.open(
            fileobj=io.BytesIO(base64.b64decode(encoded)), mode="r:gz"
        ) as archive:
            members = archive.getmembers()
            names = sorted(
                member.name.removeprefix(prefix)
                for member in members
                if member.name.startswith(prefix)
            )
            contents = b"".join(
                archive.extractfile(member).read()
                for member in members
                if member.isfile()
            )
        return names, contents, warnings

    def assert_only_kept_is_sent(self, names):
        self.assertEqual(names, ["kept"])

    def test_symlink_to_a_file_is_not_sent_and_the_user_is_told(self):
        target = self.outside / "key"
        (self.dots / "innocent").symlink_to(target)
        names, contents, warnings = self.encode()
        self.assert_only_kept_is_sent(names)
        self.assertNotIn(SECRET, contents)
        self.assertEqual(len(warnings), 1)
        self.assertIn("innocent", warnings[0])
        self.assertIn(str(target), warnings[0])
        self.assertIn("symlinks aren't supported", warnings[0])

    def test_symlink_to_a_dir_is_not_entered(self):
        (self.dots / "linked").symlink_to(self.outside)
        names, contents, warnings = self.encode()
        self.assert_only_kept_is_sent(names)
        self.assertNotIn(SECRET, contents)
        self.assertEqual(len(warnings), 1)
        self.assertIn("linked", warnings[0])

    def test_nested_symlink_is_named_by_its_path_in_the_dir(self):
        (self.dots / "sub").mkdir()
        (self.dots / "sub" / "link").symlink_to(self.outside / "key")
        names, _, warnings = self.encode()
        self.assertEqual(names, ["kept", "sub"])
        self.assertIn("sub/link", warnings[0])

    def test_broken_symlink_doesnt_crash(self):
        (self.dots / "gone").symlink_to("/nonexistent/target")
        names, _, warnings = self.encode()
        self.assert_only_kept_is_sent(names)
        self.assertIn("gone", warnings[0])

    def test_symlink_loops_dont_crash(self):
        (self.dots / "self").symlink_to(".")
        (self.dots / "up").symlink_to("..")
        (self.dots / "one").symlink_to("two")
        (self.dots / "two").symlink_to("one")
        names, _, warnings = self.encode()
        self.assert_only_kept_is_sent(names)
        self.assertEqual(len(warnings), 4)

    def test_dotfiles_dir_itself_may_be_a_symlink(self):
        link = self.root / "link_to_dots"
        link.symlink_to(self.dots)
        self.dots = link
        names, _, warnings = self.encode()
        self.assert_only_kept_is_sent(names)
        self.assertEqual(warnings, [])

    def test_no_warnings_without_symlinks(self):
        _, _, warnings = self.encode()
        self.assertEqual(warnings, [])

    def test_warnings_are_optional(self):
        (self.dots / "gone").symlink_to("/nonexistent/target")
        self.assertTrue(Payload("", self.dots).encode())
