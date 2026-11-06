"""A curses window wrapper that clips writes instead of raising."""

import contextlib
import curses
from enum import IntEnum

# curses raises when writing the bottom-right cell, so the last column is unused.
UNUSED_LAST_COLUMNS = 1
# Gap kept between right-aligned text and the edge.
RIGHT_MARGIN = 2
TITLE = "ssh-tote"
TITLE_ROW = 0


class Color(IntEnum):
    TITLE = 1
    NOTE = 2
    SELECTED = 3
    ERROR = 4


FOREGROUNDS = {
    Color.TITLE: curses.COLOR_CYAN,
    Color.NOTE: curses.COLOR_YELLOW,
    Color.SELECTED: curses.COLOR_GREEN,
    Color.ERROR: curses.COLOR_RED,
}
TERMINAL_DEFAULT = -1


class Screen:
    def __init__(self, window):
        self._window = window
        curses.curs_set(0)
        curses.use_default_colors()
        self._has_colors = curses.has_colors()
        if self._has_colors:
            for color, foreground in FOREGROUNDS.items():
                curses.init_pair(color, foreground, TERMINAL_DEFAULT)

    @property
    def height(self):
        return self._window.getmaxyx()[0]

    @property
    def width(self):
        return self._window.getmaxyx()[1]

    def style(self, color, extra=curses.A_NORMAL):
        if self._has_colors:
            return curses.color_pair(color) | extra
        return extra

    def write(self, row, column, text, style=curses.A_NORMAL):
        """Write text, clipped to the screen. Off-screen writes are ignored."""
        available = self.width - UNUSED_LAST_COLUMNS - column
        if 0 <= row < self.height and available > 0:
            with contextlib.suppress(curses.error):
                self._window.addstr(row, column, text[:available], style)

    def write_title(self, subtitle, style=curses.A_NORMAL):
        self.write(TITLE_ROW, 1, TITLE, self.style(Color.TITLE, curses.A_BOLD))
        self.write(TITLE_ROW, len(TITLE) + 2, subtitle, style)

    def write_right(self, row, text, style=curses.A_NORMAL):
        self.write(row, self.width - len(text) - RIGHT_MARGIN, text, style)

    def write_line(self, row, column, text, style=curses.A_NORMAL):
        """Write text padded to the full width, so highlighting spans the row."""
        self.write(row, column, text.ljust(self.width - column - RIGHT_MARGIN), style)

    def clear(self):
        self._window.erase()

    def refresh(self):
        self._window.refresh()

    def read_key(self):
        return self._window.get_wch()
