"""Second TUI screen: choose which variables and aliases to send."""

import curses

from ..bootstrap import human_size
from ..items import Kind, of_kind
from .screen import UNUSED_LAST_COLUMNS, Color
from .widgets import (
    ENTER_KEYS,
    ESCAPE,
    TEXT_CURSOR,
    Finished,
    ScrollingList,
    bind,
    edit_text,
    keep_end,
)

TABS_ROW = 1
FILTER_ROW = 2
LIST_TOP = 3
FOOTER_LINES = 2
MIN_NAME_WIDTH = 8
MAX_NAME_WIDTH = 32
NEWLINE_SYMBOL = "⏎"
CONFIG_LABEL = "source of truth: "
HELP = "space toggle · a/n all/none · / filter · tab · s save · enter connect · q quit"


class ItemFormatter:
    def __init__(self, local_home):
        self.local_home = local_home

    def row(self, item, name_width):
        checkbox = "[x]" if item.selected else "[ ]"
        return f" {checkbox} {item.name:<{name_width}}  {self.value(item)}"

    def value(self, item):
        shown = item.value.replace("\n", NEWLINE_SYMBOL)
        if item.kind is Kind.ENV and self.local_home not in ("", "/"):
            shown = shown.replace(self.local_home, "~")
        return shown


class Filter:
    def __init__(self):
        self.text = ""
        self.editing = False

    @property
    def is_shown(self):
        return self.editing or bool(self.text)

    @property
    def label(self):
        return f"/{self.text}" + (TEXT_CURSOR if self.editing else "")

    def matches(self, item):
        query = self.text.lower()
        return query in item.name.lower() or query in item.value.lower()

    def start_editing(self):
        self.editing = True

    def clear(self):
        self.text = ""
        self.editing = False

    def handle(self, key):
        if key in ENTER_KEYS:
            self.editing = False
        elif key == ESCAPE:
            self.clear()
        else:
            edited = edit_text(self.text, key)
            if edited is not None:
                self.text = edited


class ItemPicker:
    def __init__(self, screen, host, session, save_defaults, config_path):
        """save_defaults() persists the choices to config_path and returns a status."""
        self.screen = screen
        self.host = host
        self.session = session
        self.save_defaults = save_defaults
        self.config_path = str(config_path)
        self.formatter = ItemFormatter(session.local_home)
        self.kind = Kind.ENV
        self.lists = {kind: ScrollingList() for kind in Kind}
        self.filter = Filter()
        self.status = ""
        self.actions = self._key_bindings()
        self._built_for = None
        self._built = None

    def run(self):
        """Return True to connect, False if the user quit."""
        while True:
            self._draw()
            outcome = self._handle(self.screen.read_key())
            if isinstance(outcome, Finished):
                return outcome.value

    def _key_bindings(self):
        return bind(
            {
                ("q",): lambda: Finished(False),
                (ESCAPE,): self._clear_filter_or_quit,
                tuple(ENTER_KEYS): self._connect,
                (curses.KEY_UP, "k"): lambda: self._list.move(-1),
                (curses.KEY_DOWN, "j"): lambda: self._list.move(1),
                (curses.KEY_PPAGE,): lambda: self._list.move(-self._page_height()),
                (curses.KEY_NPAGE,): lambda: self._list.move(self._page_height()),
                (curses.KEY_HOME, "g"): lambda: self._list.jump_to(0),
                (curses.KEY_END, "G"): lambda: self._list.jump_to(
                    len(self._visible()) - 1
                ),
                (
                    "\t",
                    curses.KEY_BTAB,
                    curses.KEY_LEFT,
                    curses.KEY_RIGHT,
                ): self._switch_tab,
                (" ",): self._toggle_current,
                ("a",): self._select_visible,
                ("n",): self._deselect_visible,
                ("/",): self.filter.start_editing,
                ("s",): self._save,
            }
        )

    @property
    def _list(self):
        return self.lists[self.kind]

    def _visible(self):
        return [
            i for i in of_kind(self.session.items, self.kind) if self.filter.matches(i)
        ]

    def _bootstrap(self):
        """The session's bootstrap, rebuilt only when the selection changes.

        Building it compresses the whole payload, too slow to do on every key.
        """
        selection = tuple(item.selected for item in self.session.items)
        if selection != self._built_for:
            self._built_for, self._built = selection, self.session.bootstrap()
        return self._built

    def _page_height(self):
        return max(1, self.screen.height - LIST_TOP - FOOTER_LINES)

    # key handling

    def _handle(self, key):
        self.status = ""
        if self.filter.editing:
            self.filter.handle(key)
            return None
        action = self.actions.get(key)
        return action() if action else None

    def _clear_filter_or_quit(self):
        if self.filter.text:
            self.filter.clear()
            return None
        return Finished(False)

    def _connect(self):
        bootstrap = self._bootstrap()
        if bootstrap.too_large:
            self.status = (
                f"payload too large ({human_size(bootstrap.size)}); deselect something"
            )
            return None
        return Finished(True)

    def _switch_tab(self):
        kinds = list(Kind)
        self.kind = kinds[(kinds.index(self.kind) + 1) % len(kinds)]

    def _toggle_current(self):
        visible = self._visible()
        if visible:
            self._list.fit(len(visible), self._page_height())
            visible[self._list.cursor].toggle()
            self._list.move(1)

    def _select_visible(self):
        for item in self._visible():
            item.selected = True

    def _deselect_visible(self):
        for item in self._visible():
            item.selected = False

    def _save(self):
        try:
            self.status = self.save_defaults()
        except OSError as error:
            self.status = f"couldn't save: {error}"

    # drawing

    def _draw(self):
        self.screen.clear()
        self._draw_header()
        self._draw_tabs()
        if self.filter.is_shown:
            self.screen.write(
                FILTER_ROW, 1, self.filter.label, self.screen.style(Color.NOTE)
            )
        self._draw_items()
        self._draw_footer()
        self.screen.refresh()

    def _draw_header(self):
        bootstrap = self._bootstrap()
        self.screen.write_title(f"→ {self.host}", curses.A_BOLD)
        size_style = (
            self.screen.style(Color.ERROR, curses.A_BOLD)
            if bootstrap.too_large
            else curses.A_DIM
        )
        self.screen.write_right(0, f"payload {human_size(bootstrap.size)}", size_style)

    def _draw_tabs(self):
        column = 1
        for kind in Kind:
            items = of_kind(self.session.items, kind)
            chosen = sum(1 for item in items if item.selected)
            label = f" {kind.value} {chosen}/{len(items)} "
            is_active = kind is self.kind
            style = curses.A_REVERSE | curses.A_BOLD if is_active else curses.A_DIM
            self.screen.write(TABS_ROW, column, label, style)
            column += len(label) + 1

    def _draw_items(self):
        visible = self._visible()
        if not visible:
            empty = "nothing here" + (
                " matching the filter" if self.filter.text else ""
            )
            self.screen.write(LIST_TOP, 3, empty, curses.A_DIM)
        longest_name = max([MIN_NAME_WIDTH, *(len(item.name) for item in visible)])
        name_width = min(MAX_NAME_WIDTH, longest_name)
        for row, index in enumerate(self._list.fit(len(visible), self._page_height())):
            is_current = index == self._list.cursor
            highlight = curses.A_REVERSE if is_current else curses.A_NORMAL
            self._draw_item(LIST_TOP + row, visible[index], name_width, highlight)

    def _draw_item(self, row, item, name_width, highlight):
        color = self.screen.style(Color.SELECTED) if item.selected else curses.A_DIM
        self.screen.write_line(
            row, 1, self.formatter.row(item, name_width), highlight | color
        )
        if item.reason:
            note_style = highlight | self.screen.style(Color.NOTE)
            self.screen.write_right(row, f" {item.reason.value} ", note_style)

    def _draw_footer(self):
        self._draw_config_path()
        if self.status:
            footer, style = self.status, self.screen.style(Color.NOTE)
        else:
            footer, style = HELP, curses.A_DIM
        self.screen.write(self.screen.height - 1, 1, footer, style)

    def _draw_config_path(self):
        room = self.screen.width - UNUSED_LAST_COLUMNS - 1 - len(CONFIG_LABEL)
        text = CONFIG_LABEL + keep_end(self.config_path, room)
        self.screen.write(self.screen.height - 2, 1, text, curses.A_DIM)
