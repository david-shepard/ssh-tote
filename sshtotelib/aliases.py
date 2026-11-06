"""Reading aliases from the user's interactive shell."""

import os
import re
import subprocess

from .items import Item, Kind
from .shellwords import split_words

# Shell name -> (command printing its aliases as re-runnable `alias` lines,
# command printing its function names). The function names let
# `initial_selection` hold back aliases that call one, such as oh-my-zsh's
# `history=omz_history`.
LISTING_COMMANDS = {
    "zsh": ("alias -L", "print -l ${(k)functions}"),
    "bash": ("alias -p", "compgen -A function"),
}
CAPTURE_TIMEOUT_SECONDS = 20
OUTPUT_MARKER = "__SSH_TOTE_ALIASES__"
FUNCTIONS_MARKER = "__SSH_TOTE_FUNCTIONS__"

# zsh global (-g) and suffix (-s) aliases have no bash equivalent.
UNPORTABLE_FLAGS = frozenset({"-g", "-s"})
# A leading `!` isn't portable: it would read as an exception in the config.
PORTABLE_NAME = re.compile(r"^[^\s='\"\\$`/!-][^\s='\"\\$`/]*$")
# zsh helpers and aliases that would point back at the local tooling.
REMOTE_UNSAFE_NAMES = frozenset(
    {"run-help", "which-command", "ssh", "sshrc", "ssh-tote"}
)


class AliasCaptureError(Exception):
    pass


def capture_aliases(shell_path, environ):
    """Return the shell's aliases as {name: value} and its function names."""
    alias_command, function_command = _listing_command(shell_path)
    command = f"{alias_command}; echo {FUNCTIONS_MARKER}; {function_command}"
    listing = _run_in_interactive_shell(shell_path, command, environ)
    aliases, _, functions = listing.partition(FUNCTIONS_MARKER)
    return parse_alias_listing(aliases), set(functions.split())


def _listing_command(shell_path):
    shell_name = os.path.basename(shell_path)
    for known_shell, command in LISTING_COMMANDS.items():
        if known_shell in shell_name:
            return command
    supported = " and ".join(LISTING_COMMANDS)
    raise AliasCaptureError(
        f"can't read aliases from {shell_name or 'unknown shell'} "
        f"({supported} are supported)"
    )


def _run_in_interactive_shell(shell_path, command, environ):
    """Run command after the shell's rc files; return only its output.

    The marker separates it from anything the rc files print themselves.
    """
    try:
        result = subprocess.run(
            [shell_path, "-ic", f"echo {OUTPUT_MARKER}; {command}"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=CAPTURE_TIMEOUT_SECONDS,
            env={**environ, "SSH_TOTE_CAPTURE": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        message = f"couldn't read aliases from {shell_path}: {error}"
        raise AliasCaptureError(message) from error
    if OUTPUT_MARKER not in result.stdout:
        raise AliasCaptureError(f"couldn't read aliases from {shell_path}")
    return result.stdout.rsplit(OUTPUT_MARKER, 1)[1]


def parse_alias_listing(text):
    """Turn `alias -L` (zsh) or `alias -p` (bash) output into {name: value}."""
    aliases = {}
    for flags, definition in _alias_statements(split_words(text)):
        name, _, value = definition.partition("=")
        if PORTABLE_NAME.match(name) and flags.isdisjoint(UNPORTABLE_FLAGS):
            aliases[name] = value
    return aliases


def _alias_statements(words):
    """Yield (flags, "name=value") for every `alias [flags] name=value`."""
    remaining = iter(words)
    for word in remaining:
        if word != "alias":
            continue
        flags = set()
        for argument in remaining:
            if "=" in argument:
                yield flags, argument
                break
            flags.add(argument)


def alias_items(aliases):
    """Every alias safe to offer. Which are sent is up to `initial_selection`."""
    names = sorted(aliases.keys() - REMOTE_UNSAFE_NAMES)
    return [Item(Kind.ALIAS, name, aliases[name]) for name in names]
