import unittest

from sshtotelib.environment import collect_environment, is_portable

ENVIRON = {
    "PATH": "/bin",
    "HOME": "/h",
    "SSH_AUTH_SOCK": "/s",
    "TERM_PROGRAM": "x",
    "bad-name": "x",
    "EDITOR": "vim",
    "AWS_PROFILE": "dev",
    "GITHUB_TOKEN": "t0k",
    "DB_PASSWORD": "pw",
}


class CollectEnvironmentTest(unittest.TestCase):
    def test_only_portable_variables_are_offered(self):
        names = [item.name for item in collect_environment(ENVIRON)]
        self.assertEqual(
            names, ["AWS_PROFILE", "DB_PASSWORD", "EDITOR", "GITHUB_TOKEN"]
        )

    def test_trailing_newline_makes_a_name_unportable(self):
        self.assertFalse(is_portable("EDITOR\n"))
