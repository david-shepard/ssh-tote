# ssh-tote

Created this tool so you could ssh to a host, bringing your local shell along (aliases, functions, env variables, etc). Far from the first of it's kind, see [Inspiration](./README#inspiration)

`ssh-tote` takes a snapshot of your live local shell (the aliases defined by
your interactive zsh or bash, plus the environment variables you choose) and
recreates it on the server. Nothing is installed remotely: the payload travels
inside the ssh command, is unpacked into `/dev/shm` (or `$TMPDIR`), and is
deleted when you log out.

> **Disclaimer:** I've tested this on my own machine, but YMMV (your mileage
> may vary). I'm not responsible for anything that happens on other setups.
> I highly recommend backing up your dotfiles and anything else important
> before trying it.

## Installation

`ssh-tote` is a [uv](https://docs.astral.sh/uv/) script with inline metadata
(PEP 723). It only uses the standard library, and uv provides a Python >= 3.11
automatically.

```sh
git clone https://github.com/david-shepard/ssh-baggage.git
ln -s "$PWD/ssh-baggage/ssh-tote.py" ~/bin/ssh-tote
```

The shebang is `#!/usr/bin/env -S uv run --script`, which needs coreutils 8.30
or newer on Linux (any current distro) and works out of the box on macOS.
Without uv, run it with a Python 3.11+ interpreter:
`python3 ssh-baggage/ssh-tote.py`.

Windows isn't supported (no `curses`, no `exec`).

## Usage

    ssh-tote me@myserver                       # like ssh, plus your chosen aliases and env
    ssh-tote -p 2222 me@myserver uptime        # ssh options and a remote command pass through
    ssh-tote                                   # TUI: pick a host, then choose what to send
    ssh-tote --tui me@myserver                 # TUI straight to the selection screen
    ssh-tote --print me@myserver               # show the generated rcfile, don't connect
    ssh-tote --dir ~/.sshrc.d me@myserver      # also ship a dotfiles dir like sshrc does

### Options

Anything that isn't an ssh-tote option is passed through to `ssh`.

| Option | Effect |
| --- | --- |
| `--tui` | Pick which variables and aliases to send before connecting. |
| `--print` | Print the generated rcfile and the ssh command; don't connect. |
| `--no-env` | Don't send the variables listed in `env`. |
| `--no-aliases` | Don't send the aliases listed in `aliases`. |
| `--dir PATH` | Also ship a dotfiles dir: its `bin/` goes on `PATH`, its `.bashrc` is sourced, and it's exported as `$SSHHOME`. |
| `--no-dir` | Ignore the `dir` setting from the config file. |
| `--shell PATH` | Local shell to read aliases from (default: `$SHELL`). |
| `--help`, `--version` | |

When stdin is a terminal, ssh-tote adds `-t` so ssh allocates one, unless you
passed `-t` or `-T` yourself.

## What gets sent

> [!WARNING]
> **Don't send secrets on a machine you share.** The payload is compressed and
> base64-encoded, not encrypted, and it travels as a command-line argument to
> `ssh`. Anyone who can list processes can decode it:
>
> * **On your machine**, for as long as the `ssh` process runs, so for the whole
>   session.
> * **On the server**, while the payload is being unpacked. That's brief, but a
>   process watcher can catch it. Under a fish or tcsh login shell it lasts the
>   whole session.
>
> Anything that records commands can keep a copy too, such as `ssh -v` output or
> command auditing on the server. Check what you're sending with `--print`.

**Environment variables:** only the ones you list in the `env` setting (see
[Settings](#settings)) or tick in the TUI. Nothing else leaves your machine, so
tokens and passwords stay home unless you name them. Values containing your
local `$HOME` are rewritten to the remote `$HOME`.

Variables that describe this machine or session are never offered, not even
in the TUI or by `env = ["*"]`: `PATH`, `HOME`, `USER`, `SHELL`, `TERM`,
`TMUX`, `DISPLAY`, prompt variables, and prefixes like `SSH_*`, `XDG_*`,
`ITERM_*`, `HOMEBREW_*` and `NVM_*` (the full list is in
`sshtotelib/environment.py`).

**Aliases:** only the ones you list in the `aliases` setting or tick in the
TUI. To find them, ssh-tote runs `$SHELL -ic 'alias -L'` (zsh) or `'alias -p'`
(bash) so your rc files load, and offers what it prints. It skips zsh global and
suffix aliases (bash can't express them), aliases starting with `!`, aliases
whose names contain shell metacharacters or control characters (zsh allows them,
bash doesn't), and aliases named `ssh`, `sshrc`, `ssh-tote`, `run-help` and `which-command`. Aliases that call one of your shell
functions (like oh-my-zsh's `history=omz_history`) start unticked even if
`aliases` lists them, because functions aren't sent and the alias would fail on
the server; tick them in the TUI if your dotfiles dir defines the function
there.

While capturing, `SSH_TOTE_CAPTURE=1` is set, so your rc file can skip slow
setup:

```sh
[ -n "$SSH_TOTE_CAPTURE" ] && return
```

**Dotfiles dir** (optional, `--dir` or the `dir` setting): shipped as-is,
except names starting with `.git`, `README` or `LICENSE`, and a file named
`ssh-tote`.

Symlinks aren't supported. A symlink inside the dir, whether it points to a file
or a directory, isn't sent, and ssh-tote prints a warning naming it just before
connecting (use `--print` to see these without connecting). To send a linked
file, copy it into the dir. The dir you pass can itself be a symlink.

> [!WARNING]
> ssh-tote doesn't check a dotfiles dir for sensitive files, so check it before
> you ship it. Anything in it is copied to the server, including `.ssh`, `.aws`,
> `.gnupg`, `.env` files and private keys. The exclusions above only apply at
> the top level, so a nested `.git` dir is sent along with any tokens in its
> config.

The whole payload has to fit in one command-line argument on the server, so
it's capped at about 117 KiB. If you go over, ssh-tote refuses to connect; trim
it with `--tui`, `--no-aliases` or a smaller `--dir`.

## On the server

The remote side first behaves like a login shell (`/etc/profile`, then the
first of `~/.bash_profile`, `~/.bash_login` or `~/.profile`; under `sh`, just
`~/.profile`), so the server's
own setup still applies. Then it layers your variables and aliases on top and,
if a dotfiles dir was shipped, puts `$SSHHOME/bin` on `PATH` and sources
`$SSHHOME/.bashrc` (under bash). It uses bash if the server has it and falls back to `sh`.

Other users on the server can read any process's command line, so once the
payload is unpacked the bootstrap replaces itself with a short start script
and the payload drops out of the server's process list. It's still exposed
until then, and on your own machine for the whole session (see the warning under
[What gets sent](#what-gets-sent)). If your login shell on the server is fish or
tcsh, that shell keeps its own copy of the command line for the whole session,
so don't send secrets there.

Remotely these are set:

| Variable | Meaning |
| --- | --- |
| `SSH_TOTE_HOME` | Temporary dir holding the payload; removed on logout. |
| `SSHHOME` | `$SSH_TOTE_HOME/dir`, the shipped dotfiles dir (same layout as sshrc). |

## Settings

Defaults live in `~/.config/ssh-tote/config.toml` (or
`$XDG_CONFIG_HOME/ssh-tote/config.toml`). Every key is optional, and a missing
file means "send no aliases and no environment variables". `ssh-tote --help` prints the
path it uses.

```toml
# Always ship this dotfiles dir (`~` is expanded). --dir overrides it,
# --no-dir ignores it.
dir = "~/.sshrc.d"

# Environment variables to send. Nothing else is sent. Shell globs allowed,
# and a leading ! is an exception (see below).
env = ["EDITOR", "PAGER", "LESS*", "AWS_*", "!AWS_SECRET_ACCESS_KEY"]

# Aliases to send. Nothing else is sent. Shell globs allowed.
aliases = ["ll", "g*"]
```

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `dir` | string | none | Dotfiles dir to ship on every connection. Must be an existing directory. |
| `env` | list of globs | `[]` | Variables to send. |
| `aliases` | list of globs | `[]` | Aliases to send. |

Patterns are shell globs (`*`, `?`, `[abc]`) and are case-sensitive. The
settings only set what's ticked by default: in the TUI you can still toggle
anything on or off for one connection.

If the file isn't valid TOML or a value has the wrong type (say, a string
instead of a list), ssh-tote prints a warning and carries on with the
defaults.

### Exceptions

In `env` and `aliases`, an entry starting with `!` is an exception: it keeps
matching items from being sent, even though another entry matches them. It can
be a name or a glob.

```toml
env = ["AWS_*", "!AWS_SECRET_ACCESS_KEY", "!AWS_SESSION_*"]
```

Unlike `.gitignore` or `.stignore`, the order of entries doesn't matter (saving
sorts them). The first of these that applies decides:

1. `!NAME`: not sent.
2. `NAME`: sent.
3. A `!glob` that matches: not sent.
4. A glob that matches: sent.

Versions before 0.5.0 treat `!NAME` as a pattern that matches nothing, so if you
downgrade, `AWS_*` above would send `AWS_SECRET_ACCESS_KEY` again.

### Upgrading from 0.3

Before 0.4.0 every alias was sent unless listed in `exclude_aliases`. That key
is now ignored, with a warning, because only aliases listed in `aliases` are
sent. Run `ssh-tote --tui`, tick the aliases you want and press `s`.

### Upgrading from 0.2

Before 0.3.0 every variable was sent unless excluded. Old config files still
load, with a warning: `include_env` is read as `env`, and `exclude_env` is
ignored because nothing is sent unless listed. Pressing `s` in the TUI writes
the file in the new form.

### Saving from the TUI

The variable and alias picker shows the config file's absolute path above its
help line, as the `source of truth`. Pressing `s` saves the current choices to
that file. Only choices that differ from what `env` and `aliases` already say
change anything:

* items you ticked are added by name, unless removing their `!NAME` exception
  is enough for a glob to send them,
* items you unticked lose their entry, and if a glob would still send them they
  get a `!NAME` exception,
* aliases marked "calls a local function" are left out either way: they're
  checked again on every run, so ticking one only lasts for this connection.

So the easiest way to set up `env` and `aliases` is to run `ssh-tote --tui` once, tick what
you want and press `s`.

Glob entries and names that don't exist in the current shell are kept. `dir`
is kept too.

> **Note:** saving rewrites the whole file, so comments and formatting you
> added by hand are lost.

### Host history

Hosts you connect to are recorded in `~/.config/ssh-tote/history` (the 50 most
recent). The host picker lists them first, followed by the `Host` entries from
`~/.ssh/config` (including `Include`d files, skipping wildcard patterns).

## TUI keys

Host picker:

| Key | Action |
| --- | --- |
| type | filter hosts, or type a new one |
| `↑` `↓` | move |
| `enter` | select |
| `esc` | quit |

Variable and alias picker:

| Key | Action |
| --- | --- |
| `space` | toggle the current item |
| `a` / `n` | select all / none (only the items the filter shows) |
| `/` | filter by name or value; `esc` clears it |
| `tab`, `←` `→` | switch between environment and aliases |
| `↑` `↓`, `j` `k` | move |
| `PgUp` `PgDn` | page |
| `g` / `G`, `Home` / `End` | first / last |
| `s` | save the choices as defaults (see [Saving from the TUI](#saving-from-the-tui)) |
| `enter` | connect |
| `q`, `esc` | quit without connecting |

## Exit status

When it connects, ssh-tote replaces itself with `ssh`, so you get ssh's exit
status. Otherwise:

| Code | Meaning |
| --- | --- |
| 0 | `--print`, `--help` or `--version` succeeded |
| 1 | cancelled in the TUI, or the payload is too large |
| 2 | usage error |
| 127 | `ssh` couldn't be run |

## Development

The entry point is `ssh-tote.py`. The code lives in `sshtotelib/`, one module per
concern: argument parsing, environment and alias collection, the rcfile, the
payload, the remote bootstrap, host history, and the TUI.

    uv run --python 3.11 -m unittest discover -s tests -t .   # tests
    uvx ruff check . && uvx ruff format --check .             # lint

## Inspiration

Heavily borrowed/inspired by the following tools:

- [theonejb/sshenv: A simple CLI utility to switch between different SSH environments.](https://github.com/theonejb/sshenv)
- [KennethanCeyer/gowap: :lock: ssh key manager written in go](https://github.com/KennethanCeyer/gowap)
- [TimothyYe/skm: A simple and powerful SSH keys manager](https://github.com/TimothyYe/skm)
- [sineemore/backpack: .bashrc over ssh](https://github.com/sineemore/backpack)

