"""Choosing which local environment variables to send."""

import re

from .items import Item, Kind

# Variables that describe this machine or terminal session and would be wrong
# on the server. They are never offered, even if `env` matches them.
# fmt: off
LOCAL_ONLY_VARIABLES = frozenset({
    "_", "PATH", "HOME", "USER", "LOGNAME", "SHELL", "PWD", "OLDPWD", "SHLVL",
    "TMPDIR", "TERM", "COLORTERM", "COLORFGBG", "TERMINFO", "TERMINFO_DIRS",
    "DISPLAY", "MAIL", "HOSTNAME", "HOST", "MANPATH", "INFOPATH", "FPATH",
    "COMMAND_MODE", "SECURITYSESSIONID", "LaunchInstanceID", "OSLogRateLimit",
    "MallocNanoZone", "PS1", "PS2", "PS4", "PROMPT", "RPROMPT",
    "PROMPT_COMMAND", "ZDOTDIR", "ZSH", "ZSH_CUSTOM", "ZSH_CACHE_DIR", "TTY",
    "GPG_TTY", "LINES", "COLUMNS", "SSHHOME", "SSHRCCLEANUP", "SSH_TOTE_HOME",
    "CLAUDECODE", "AI_AGENT", "VIRTUAL_ENV", "CONDA_PREFIX",
    "CONDA_DEFAULT_ENV", "PYENV_SHELL", "LESSOPEN", "LESSCLOSE",
    "DBUS_SESSION_BUS_ADDRESS", "XAUTHORITY", "WAYLAND_DISPLAY",
    "SESSION_MANAGER", "TMUX", "TMUX_PANE", "STY", "WINDOW", "WINDOWID",
})
LOCAL_ONLY_PREFIXES = (
    "SSH_", "XPC_", "Apple_", "TERM_", "ITERM_", "LC_TERMINAL",
    "KITTY_", "ALACRITTY_", "WEZTERM_", "GHOSTTY_", "VSCODE_", "WT_",
    "KONSOLE_", "GNOME_", "XDG_", "NVM_", "HOMEBREW_", "DIRENV_", "P9K_",
    "_P9K", "POWERLEVEL9K_", "STARSHIP_", "ZELLIJ", "ATUIN_", "CLAUDE_",
    "_ZSH", "__",
)
# fmt: on
PORTABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def collect_environment(environ):
    """Every portable variable. Which are sent is up to `initial_selection`."""
    names = sorted(name for name in environ if is_portable(name))
    return [Item(Kind.ENV, name, environ[name]) for name in names]


def is_portable(name):
    is_local_only = name in LOCAL_ONLY_VARIABLES or name.startswith(LOCAL_ONLY_PREFIXES)
    return bool(PORTABLE_NAME.match(name)) and not is_local_only
