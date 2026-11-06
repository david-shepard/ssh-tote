import unittest

from sshtotelib.arguments import UsageError, parse_arguments


class HostAndCommandTest(unittest.TestCase):
    def test_host_is_first_positional_argument(self):
        self.assertEqual(parse_arguments(["me@box", "ls"]).host, "me@box")

    def test_everything_after_host_is_the_remote_command(self):
        self.assertEqual(parse_arguments(["box", "ls", "-la"]).command, ["ls", "-la"])

    def test_options_after_host_belong_to_the_command(self):
        self.assertEqual(parse_arguments(["box", "--tui"]).command, ["--tui"])

    def test_double_dash_marks_the_host(self):
        self.assertEqual(parse_arguments(["--", "-weird-host"]).host, "-weird-host")


class SshOptionsTest(unittest.TestCase):
    def test_options_with_separate_values(self):
        options = parse_arguments(["-p", "2222", "-v", "-i", "key", "box"])
        self.assertEqual(options.ssh_args, ["-p", "2222", "-v", "-i", "key"])

    def test_bundled_flags_ending_in_option_with_value(self):
        self.assertEqual(parse_arguments(["-vp", "22", "box"]).ssh_args, ["-vp", "22"])

    def test_attached_value(self):
        self.assertEqual(parse_arguments(["-p22", "box"]).ssh_args, ["-p22"])

    def test_missing_value_is_a_usage_error(self):
        with self.assertRaises(UsageError):
            parse_arguments(["-p"])


class SshToteOptionsTest(unittest.TestCase):
    def test_negative_flags_turn_features_off(self):
        options = parse_arguments(["--no-env", "--no-aliases", "box"])
        self.assertEqual((options.send_env, options.send_aliases), (False, False))

    def test_value_option_with_equals(self):
        self.assertEqual(
            parse_arguments(["--dir=~/dots", "box"]).dotfiles_dir, "~/dots"
        )

    def test_value_option_with_separate_value(self):
        self.assertEqual(
            parse_arguments(["--shell", "/bin/bash", "box"]).shell, "/bin/bash"
        )

    def test_value_option_without_value_is_a_usage_error(self):
        with self.assertRaises(UsageError):
            parse_arguments(["--dir"])

    def test_unknown_long_option_is_a_usage_error(self):
        with self.assertRaises(UsageError):
            parse_arguments(["--bogus", "box"])
