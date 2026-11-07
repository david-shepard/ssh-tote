"""Everything one connection will carry, and how it becomes a bootstrap."""

from dataclasses import dataclass
from pathlib import Path

from .bootstrap import Bootstrap
from .payload import Payload
from .rcfile import (
    DOTFILES_SECTION,
    LOGIN_SECTION,
    SELF_DELETE_SECTION,
    alias_section,
    command_section,
    environment_section,
    join_sections,
)


@dataclass
class Session:
    items: list
    local_home: str
    dotfiles_dir: Path | None = None
    command: str | None = None

    def rcfile(self):
        sections = [
            SELF_DELETE_SECTION,
            LOGIN_SECTION,
            environment_section(self.items, self.local_home),
            alias_section(self.items),
        ]
        if self.dotfiles_dir:
            sections.append(DOTFILES_SECTION)
        if self.command:
            sections.append(command_section(self.command))
        return join_sections(sections)

    def bootstrap(self, warn=lambda message: None):
        payload = Payload(self.rcfile(), self.dotfiles_dir)
        return Bootstrap.for_payload(payload.encode(warn))
