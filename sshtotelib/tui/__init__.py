"""Interactive host and item selection."""

import curses
import locale
import os

from .host_picker import HostPicker
from .item_picker import ItemPicker
from .screen import Screen

# Milliseconds curses waits after Esc to tell it apart from an arrow key.
ESCAPE_DELAY_MS = 25


def prepare_terminal():
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", str(ESCAPE_DELAY_MS))


def choose_interactively(host, choices, session, save_defaults, config_path):
    """Run the pickers. Returns the host to connect to, or None if cancelled.

    When `host` is already known the host picker is skipped. The user's
    choices are applied to `session.items` in place.
    """

    def run(window):
        screen = Screen(window)
        chosen = host or HostPicker(screen, choices).run()
        if not chosen:
            return None
        picker = ItemPicker(screen, chosen, session, save_defaults, config_path)
        return chosen if picker.run() else None

    return curses.wrapper(run)
