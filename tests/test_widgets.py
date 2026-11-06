import curses
import unittest

from sshtotelib.tui.widgets import ScrollingList, edit_text


class ScrollingListTest(unittest.TestCase):
    def test_cursor_is_clamped_to_the_list(self):
        rows = ScrollingList()
        rows.move(99)
        rows.fit(count=5, height=10)
        self.assertEqual(rows.cursor, 4)

    def test_window_follows_the_cursor_down(self):
        rows = ScrollingList()
        rows.jump_to(7)
        self.assertEqual(rows.fit(count=20, height=3), range(5, 8))

    def test_empty_list(self):
        self.assertEqual(ScrollingList().fit(count=0, height=3), range(0, 0))


class EditTextTest(unittest.TestCase):
    def test_typing_appends(self):
        self.assertEqual(edit_text("ab", "c"), "abc")

    def test_backspace_removes_last_char(self):
        self.assertEqual(edit_text("a", curses.KEY_BACKSPACE), "")

    def test_other_keys_are_not_edits(self):
        self.assertIsNone(edit_text("ab", curses.KEY_UP))
