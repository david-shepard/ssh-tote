import tempfile
import unittest
from pathlib import Path

from sshtotelib.hosts import History, HostChoice, host_choices, ssh_config_hosts


class HostsTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)


class SshConfigHostsTest(HostsTestCase):
    def test_concrete_hosts_including_relative_includes(self):
        (self.dir / "extra").write_text("Host included\n")
        config = self.dir / "config"
        config.write_text(
            "Host a b *.wild\n  HostName x\n# Host commented\n"
            "Host=c\nInclude extra\nHost !negated\nInclude config\n"
        )
        self.assertEqual(ssh_config_hosts(config), ["a", "b", "c", "included"])


class HistoryTest(HostsTestCase):
    def test_record_moves_host_to_front_without_duplicates(self):
        history = History(self.dir / "sub" / "history")
        for host in ("a", "b", "a"):
            history.record(host)
        self.assertEqual(history.hosts(), ["a", "b"])


class HostChoicesTest(HostsTestCase):
    def test_recent_hosts_come_first_and_are_not_repeated(self):
        history = History(self.dir / "history")
        history.record("b")
        (self.dir / "config").write_text("Host a b\n")
        expected = [HostChoice("b", "recent"), HostChoice("a", "ssh config")]
        self.assertEqual(host_choices(history, self.dir / "config"), expected)
