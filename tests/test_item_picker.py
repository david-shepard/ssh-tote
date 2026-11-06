import unittest
from unittest import mock

from sshtotelib.items import Item, Kind
from sshtotelib.session import Session
from sshtotelib.tui.item_picker import ItemPicker
from sshtotelib.tui.screen import UNUSED_LAST_COLUMNS

CONFIG_PATH = "/home/you/.config/ssh-tote/config.toml"


class FakeScreen:
    """Records the text drawn on each row."""

    def __init__(self, width=120, height=24):
        self.width = width
        self.height = height
        self.rows = {}

    def style(self, color, extra=0):
        return extra

    def clear(self):
        self.rows = {}

    def refresh(self):
        pass

    def write(self, row, column, text, style=0):
        self.rows[row] = text

    def write_line(self, row, column, text, style=0):
        self.rows[row] = text

    def write_right(self, row, text, style=0):
        pass

    def write_title(self, subtitle, style=0):
        pass


def picker_on(screen, save_defaults=None):
    session = Session([Item(Kind.ENV, "EDITOR", "vim")], local_home="/h")
    return ItemPicker(screen, "box", session, save_defaults, CONFIG_PATH)


class ItemPickerBootstrapTest(unittest.TestCase):
    def test_bootstrap_is_rebuilt_only_when_the_selection_changes(self):
        picker = picker_on(None)
        session = picker.session
        with mock.patch.object(session, "bootstrap", wraps=session.bootstrap) as build:
            picker._bootstrap()
            picker._bootstrap()
            session.items[0].toggle()
            picker._bootstrap()
        self.assertEqual(build.call_count, 2)


class ItemPickerFooterTest(unittest.TestCase):
    def test_config_path_sits_above_the_help_line(self):
        screen = FakeScreen()
        picker_on(screen)._draw()
        self.assertEqual(screen.rows[22], f"source of truth: {CONFIG_PATH}")
        self.assertTrue(screen.rows[23].startswith("space toggle"))

    def test_help_line_fits_an_80_column_terminal(self):
        screen = FakeScreen(width=80)
        picker_on(screen)._draw()
        help_line = screen.rows[23]
        self.assertLessEqual(len(help_line), 80 - UNUSED_LAST_COLUMNS - 1)
        self.assertIn("enter connect", help_line)
        self.assertIn("q quit", help_line)

    def test_config_path_stays_when_a_status_replaces_the_help_line(self):
        screen = FakeScreen()
        picker = picker_on(screen, save_defaults=lambda: "saved")
        picker._handle("s")
        picker._draw()
        self.assertEqual(screen.rows[22], f"source of truth: {CONFIG_PATH}")
        self.assertEqual(screen.rows[23], "saved")

    def test_long_config_path_keeps_its_end(self):
        screen = FakeScreen(width=40)
        picker_on(screen)._draw()
        self.assertEqual(screen.rows[22], "source of truth: …ssh-tote/config.toml")
