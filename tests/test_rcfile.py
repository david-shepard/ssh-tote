import unittest

from sshtotelib.rcfile import quote_with_remote_home

HOME = "/h"


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
