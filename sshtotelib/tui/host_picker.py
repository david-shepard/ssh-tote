"""First TUI screen: choose where to connect."""

import curses

from ..hosts import HostChoice
from .screen import Color
from .widgets import (
    ENTER_KEYS,
    ESCAPE,
    TEXT_CURSOR,
    Finished,
    ScrollingList,
    bind,
    edit_text,
)

INPUT_ROW = 2
INPUT_LABEL = "host: "
LIST_TOP = 4
FOOTER_LINES = 2
HOST_COLUMN_WIDTH = 40
HELP = "type to filter · ↑↓ move · enter select · esc quit"
NO_HOSTS = "no hosts in history or ~/.ssh/config — type one"
TYPED_SOURCE = "typed"


class HostPicker:
    def __init__(self, screen, choices):
        self.screen = screen
        self.choices = choices
        self.query = ""
        self.list = ScrollingList()
        self.actions = bind(
            {
                (ESCAPE,): lambda: Finished(None),
                tuple(ENTER_KEYS): self._choose,
                (curses.KEY_UP,): lambda: self.list.move(-1),
                (curses.KEY_DOWN,): lambda: self.list.move(1),
            }
        )

    def run(self):
        """Return the chosen host name, or None if the user quit."""
        while True:
            self._draw()
            outcome = self._handle(self.screen.read_key())
            if isinstance(outcome, Finished):
                return outcome.value

    def _rows(self):
        """Choices matching the query, an exact match first.

        Without an exact match the typed text is offered last, so a host whose
        name is part of a listed one (`prod` next to `prod-db`) can be chosen.
        """
        typed = self.query.strip()
        query = typed.lower()
        matching = [choice for choice in self.choices if query in choice.name.lower()]
        exact = [choice for choice in matching if choice.name == typed]
        others = [choice for choice in matching if choice.name != typed]
        if typed and not exact:
            others.append(HostChoice(typed, TYPED_SOURCE))
        return exact + others

    def _handle(self, key):
        edited = edit_text(self.query, key)
        if edited is not None:
            self.query = edited
            self.list.jump_to(0)
            return None
        action = self.actions.get(key)
        return action() if action else None

    def _choose(self):
        rows = self._rows()
        return Finished(rows[self.list.cursor].name) if rows else None

    def _draw(self):
        screen = self.screen
        screen.clear()
        screen.write_title("— where to?")
        screen.write(INPUT_ROW, 1, INPUT_LABEL, curses.A_BOLD)
        screen.write(INPUT_ROW, 1 + len(INPUT_LABEL), self.query + TEXT_CURSOR)
        self._draw_choices()
        screen.write(screen.height - 1, 1, HELP, curses.A_DIM)
        screen.refresh()

    def _draw_choices(self):
        rows = self._rows()
        if not rows:
            self.screen.write(LIST_TOP, 3, NO_HOSTS, self.screen.style(Color.NOTE))
        height = max(1, self.screen.height - LIST_TOP - FOOTER_LINES)
        for row, index in enumerate(self.list.fit(len(rows), height)):
            choice = rows[index]
            highlight = (
                curses.A_REVERSE if index == self.list.cursor else curses.A_NORMAL
            )
            text = f" {choice.name:<{HOST_COLUMN_WIDTH}} {choice.source} "
            self.screen.write_line(LIST_TOP + row, 1, text, highlight)
