"""Command-line entry point: work out what to send, then hand over to ssh."""

import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from . import VERSION, tui
from .aliases import AliasCaptureError, alias_items, capture_aliases
from .arguments import USAGE, UsageError, parse_arguments
from .bootstrap import MAX_BOOTSTRAP_BYTES, human_size
from .environment import collect_environment
from .hosts import History, host_choices
from .selection import initial_selection, remember_selection
from .session import Session
from .settings import Settings, SettingsError, SettingsFile

EXIT_OK = 0
EXIT_NOT_CONNECTED = 1
EXIT_USAGE = 2
EXIT_SSH_NOT_RUNNABLE = 127


@dataclass(frozen=True)
class Paths:
    settings: Path
    history: Path
    ssh_config: Path

    @classmethod
    def from_environment(cls, environ):
        config_home = environ.get("XDG_CONFIG_HOME") or "~/.config"
        config_dir = Path(config_home).expanduser().absolute() / "ssh-tote"
        return cls(
            settings=config_dir / "config.toml",
            history=config_dir / "history",
            ssh_config=Path("~/.ssh/config").expanduser(),
        )


def main(argv=None, environ=os.environ):
    paths = Paths.from_environment(environ)
    usage = USAGE.format(settings_path=paths.settings)
    try:
        options = parse_arguments(sys.argv[1:] if argv is None else argv)
    except UsageError as error:
        return _fail(f"{error}\n\n{usage}", EXIT_USAGE)
    if options.show_help:
        print(usage, end="")
        return EXIT_OK
    if options.show_version:
        print(f"ssh-tote {VERSION}")
        return EXIT_OK
    try:
        return _connect(options, paths, environ, usage)
    except UsageError as error:
        return _fail(error, EXIT_USAGE)


def _connect(options, paths, environ, usage):
    settings = _load_settings(paths.settings)
    session = _build_session(options, settings, environ)
    host = options.host
    if options.interactive or host is None:
        host = _choose_interactively(host, session, settings, paths, usage)
    if host is None:
        return EXIT_NOT_CONNECTED

    # Only here: the TUI rebuilds the bootstrap as you tick, under curses.
    bootstrap = session.bootstrap(warn=_warn)
    if bootstrap.too_large:
        return _fail(_too_large_message(bootstrap), EXIT_NOT_CONNECTED)
    ssh_command = ["ssh", *_tty_options(options), *options.ssh_args, host]
    if options.dry_run:
        _print_dry_run(session, ssh_command, bootstrap)
        return EXIT_OK
    History(paths.history).record(host)
    return _exec_ssh([*ssh_command, bootstrap.command])


def _too_large_message(bootstrap):
    return (
        f"payload is {human_size(bootstrap.size)}, over the "
        f"{human_size(MAX_BOOTSTRAP_BYTES)} limit. "
        "Use --tui, --no-aliases or a smaller --dir."
    )


def _load_settings(path):
    try:
        return SettingsFile(path).load(warn=_warn)
    except SettingsError as error:
        _warn(f"ignoring {error}")
        return Settings()


def _build_session(options, settings, environ):
    items, local_functions = [], set()
    if options.send_env:
        items += collect_environment(environ)
    if options.send_aliases:
        shell = options.shell or environ.get("SHELL", "")
        aliases, local_functions = _collect_aliases(shell, environ)
        items += aliases
    return Session(
        items=initial_selection(items, settings, local_functions),
        local_home=environ.get("HOME", ""),
        dotfiles_dir=_dotfiles_dir(options, settings),
        command=" ".join(options.command) or None,
    )


def _collect_aliases(shell, environ):
    try:
        aliases, functions = capture_aliases(shell, environ)
    except AliasCaptureError as error:
        _warn(error)
        return [], set()
    return alias_items(aliases), functions


def _dotfiles_dir(options, settings):
    configured = settings.dotfiles_dir if options.use_configured_dir else None
    chosen = options.dotfiles_dir or configured
    if chosen is None:
        return None
    path = Path(chosen).expanduser()
    if not path.is_dir():
        raise UsageError(f"dotfiles dir {chosen}: not a directory")
    return path


def _choose_interactively(host, session, settings, paths, usage):
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise UsageError(f"the TUI needs a terminal\n\n{usage}")

    def save_defaults():
        SettingsFile(paths.settings).save(remember_selection(settings, session.items))
        return f"saved defaults to {paths.settings}"

    tui.prepare_terminal()
    choices = host_choices(History(paths.history), paths.ssh_config)
    return tui.choose_interactively(
        host, choices, session, save_defaults, paths.settings
    )


def _tty_options(options):
    """Ask ssh for a terminal, unless the user decided (-t/-T) or has none."""
    user_decided = bool({"-t", "-T"} & set(options.ssh_args))
    if sys.stdin.isatty() and not user_decided:
        return ["-t"]
    return []


def _print_dry_run(session, ssh_command, bootstrap):
    print(session.rcfile(), end="")
    shown = " ".join(shlex.quote(part) for part in ssh_command)
    print(f"\n# {shown} <bootstrap, {human_size(bootstrap.size)}>")


def _exec_ssh(command):
    try:
        os.execvp(command[0], command)
    except OSError as error:
        return _fail(f"can't run ssh: {error}", EXIT_SSH_NOT_RUNNABLE)


def _warn(message):
    print(f"ssh-tote: {message}", file=sys.stderr)


def _fail(message, exit_code):
    _warn(message)
    return exit_code
