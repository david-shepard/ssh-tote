"""The things ssh-tote can carry to a remote shell."""

from dataclasses import dataclass
from enum import Enum


class Kind(Enum):
    ENV = "Environment"
    ALIAS = "Aliases"


class Reason(Enum):
    """Why an item is held back. The value is the note the TUI shows."""

    CALLS_LOCAL_FUNCTION = "calls a local function"


@dataclass
class Item:
    kind: Kind
    name: str
    value: str
    selected: bool = True
    reason: Reason | None = None

    def toggle(self):
        self.selected = not self.selected


def of_kind(items, kind):
    return [item for item in items if item.kind is kind]


def selected_of_kind(items, kind):
    return [item for item in of_kind(items, kind) if item.selected]
