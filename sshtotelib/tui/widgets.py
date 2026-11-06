"""Building blocks shared by the TUI screens."""

import curses
from dataclasses import dataclass

ESCAPE = "\x1b"
ENTER_KEYS = frozenset({"\n", "\r", curses.KEY_ENTER})
BACKSPACE_KEYS = frozenset({curses.KEY_BACKSPACE, "\x7f", "\b"})
TEXT_CURSOR = "▏"


@dataclass(frozen=True)
class Finished:
    """Returned by a key handler to end a screen with `value`."""

    value: object


def bind(bindings):
    """Expand {(key, key, ...): action} into {key: action}."""
    return {key: action for keys, action in bindings.items() for key in keys}


def edit_text(text, key):
    """Apply a typing key to text, or return None if key doesn't edit text."""
    if key in BACKSPACE_KEYS:
        return text[:-1]
    if isinstance(key, str) and key.isprintable():
        return text + key
    return None


def keep_end(text, width):
    """Text cut to `width` from the left, for paths whose end matters most."""
    return text if len(text) <= width else "…" + text[len(text) - width + 1 :]


class ScrollingList:
    """A cursor and scroll offset over a list whose length keeps changing.

    All clamping lives in `fit`, so moves can overshoot freely.
    """

    def __init__(self):
        self.cursor = 0
        self.top = 0

    def move(self, delta):
        self.cursor += delta

    def jump_to(self, index):
        self.cursor = index

    def fit(self, count, height):
        """Clamp to `count` rows and return the indexes visible in `height` rows."""
        self.cursor = max(0, min(self.cursor, count - 1))
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + height:
            self.top = self.cursor - height + 1
        self.top = max(0, min(self.top, count - height))
        return range(self.top, min(count, self.top + height))
