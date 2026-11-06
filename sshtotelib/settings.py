"""User defaults, stored as TOML in ~/.config/ssh-tote/config.toml."""

import json
import pathlib
import tomllib
from dataclasses import dataclass, field

HEADER = (
    '# ssh-tote config. Entries may use shell globs, e.g. "AWS_*", and a leading !'
    '\n# keeps matches from being sent, e.g. "!AWS_SECRET*". Order doesn\'t matter.'
)
PATTERN_LISTS = ("env", "aliases")
# Keys from before 0.3.0 (variables) and 0.4.0 (aliases), when everything was
# sent unless excluded.
OLD_INCLUDE_ENV = "include_env"
OLD_KEYS = {
    OLD_INCLUDE_ENV: "is now called `env`; its entries are used as `env`",
    "exclude_env": "is ignored; only variables listed in `env` are sent",
    "exclude_aliases": "is ignored; only aliases listed in `aliases` are sent",
}


class SettingsError(Exception):
    pass


@dataclass
class Settings:
    dotfiles_dir: str | None = None
    env: set = field(default_factory=set)
    aliases: set = field(default_factory=set)


class SettingsFile:
    def __init__(self, path: pathlib.Path):
        self.path = path

    def load(self, warn=lambda message: None):
        try:
            with open(self.path, "rb") as file:
                data = tomllib.load(file)
        except FileNotFoundError:
            return Settings()
        except tomllib.TOMLDecodeError as error:
            raise SettingsError(f"invalid config {self.path}: {error}") from error
        dotfiles_dir = data.get("dir")
        if not isinstance(dotfiles_dir, str | None):
            raise SettingsError(f"invalid config {self.path}: dir must be a string")
        lists = {key: data.get(key, []) for key in (*PATTERN_LISTS, OLD_INCLUDE_ENV)}
        for key, patterns in lists.items():
            if not _is_list_of_strings(patterns):
                message = f"invalid config {self.path}: {key} must be a list of strings"
                raise SettingsError(message)
        for key, change in OLD_KEYS.items():
            if key in data:
                warn(f"{self.path}: `{key}` {change}")
        lists["env"] += lists.pop(OLD_INCLUDE_ENV)
        return Settings(dotfiles_dir, **{k: set(v) for k, v in lists.items()})

    def save(self, settings):
        lines = [HEADER, ""]
        if settings.dotfiles_dir:
            lines.append(f"dir = {json.dumps(settings.dotfiles_dir)}")
        for key in PATTERN_LISTS:
            lines += _toml_list(key, getattr(settings, key))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(lines) + "\n")


def _is_list_of_strings(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _toml_list(key, values):
    entries = [f"  {json.dumps(value)}," for value in sorted(values)]
    return [f"{key} = [", *entries, "]"]
