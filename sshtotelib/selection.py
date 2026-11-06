"""Which items start ticked, and what saving remembers about the selection."""

import dataclasses
import fnmatch

from .items import Kind, Reason, of_kind
from .settings import Settings
from .shellwords import split_words

# Kind -> the Settings list naming the items of that kind to send.
SEND_PATTERNS = {Kind.ENV: "env", Kind.ALIAS: "aliases"}
EXCEPTION_PREFIX = "!"


def initial_selection(items, settings, local_functions):
    """Copies of `items`, ticked the way `settings` asks, with hold-backs unticked."""
    return [_with_default(item, settings, local_functions) for item in items]


def _with_default(item, settings, local_functions):
    # Functions aren't sent, so an alias that calls one would fail on the server.
    if item.kind is Kind.ALIAS and _command_word(item.value) in local_functions:
        return dataclasses.replace(
            item, selected=False, reason=Reason.CALLS_LOCAL_FUNCTION
        )
    patterns = getattr(settings, SEND_PATTERNS[item.kind])
    return dataclasses.replace(item, selected=_is_sent(item.name, patterns))


def remember_selection(settings, items):
    """Settings updated so future runs make the same choices as `items`.

    Only items the config says otherwise about change anything, so entries for
    names that are not in `items` (variables that are unset right now) and
    globs are kept untouched. Hold-backs are decided afresh on every run, so
    they are never remembered, ticked or not.
    """
    chosen = [item for item in items if not _is_hold_back(item)]
    lists = {
        key: _with_choices(getattr(settings, key), of_kind(chosen, kind))
        for kind, key in SEND_PATTERNS.items()
    }
    return Settings(dotfiles_dir=settings.dotfiles_dir, **lists)


def _is_hold_back(item):
    return item.reason is not None


def _with_choices(patterns, items):
    patterns = set(patterns)
    for item in items:
        if _is_sent(item.name, patterns) != item.selected:
            patterns -= {item.name, EXCEPTION_PREFIX + item.name}
        if _is_sent(item.name, patterns) != item.selected:
            prefix = "" if item.selected else EXCEPTION_PREFIX
            patterns.add(prefix + item.name)
    return patterns


def _is_sent(name, patterns):
    """What the config says about `name`. The order of entries doesn't matter.

    An exact entry decides, so saving can always record a choice; `!NAME` beats
    `NAME`. Otherwise an exception that matches beats a glob that matches.
    """
    if EXCEPTION_PREFIX + name in patterns:
        return False
    if name in patterns:
        return True
    exceptions = {p for p in patterns if p.startswith(EXCEPTION_PREFIX)}
    unprefixed = {exception[len(EXCEPTION_PREFIX) :] for exception in exceptions}
    return not _matches_any(name, unprefixed) and _matches_any(
        name, patterns - exceptions
    )


def _matches_any(name, patterns):
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def _command_word(value):
    words = split_words(value)
    return words[0] if words else ""
