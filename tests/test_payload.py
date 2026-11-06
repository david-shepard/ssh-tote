import os
import tempfile
import unittest
from pathlib import Path

from sshtotelib.bootstrap import MAX_BOOTSTRAP_BYTES, Bootstrap
from sshtotelib.payload import Payload

FILE_BYTES = 100_000
FILE_COUNT = 20


class PayloadTest(unittest.TestCase):
    def test_huge_dotfiles_dir_stops_early_but_is_still_too_large(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(FILE_COUNT):
                Path(directory, f"f{index:02}").write_bytes(os.urandom(FILE_BYTES))
            encoded = Payload("", Path(directory)).encode()
        self.assertTrue(Bootstrap.for_payload(encoded).too_large)
        # Random bytes don't compress, so reading every file would be ~2.7 MB.
        self.assertLess(len(encoded), 4 * MAX_BOOTSTRAP_BYTES)
