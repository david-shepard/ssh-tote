import unittest

from sshtotelib.hosts import HostChoice
from sshtotelib.tui.host_picker import HostPicker

CHOICES = [HostChoice("prod-db", "recent"), HostChoice("prod", "ssh config")]


def rows(query, choices=CHOICES):
    picker = HostPicker(screen=None, choices=choices)
    picker.query = query
    return [choice.name for choice in picker._rows()]


class HostPickerRowsTest(unittest.TestCase):
    def test_exact_match_comes_first(self):
        self.assertEqual(rows("prod"), ["prod", "prod-db"])

    def test_typed_host_is_offered_when_only_a_longer_name_matches(self):
        self.assertEqual(rows("prod", CHOICES[:1]), ["prod-db", "prod"])

    def test_empty_query_lists_everything(self):
        self.assertEqual(rows(""), ["prod-db", "prod"])
