"""Separating ssh-tote's own options from the ones passed through to ssh."""

from dataclasses import dataclass, field

# ssh options that take a value (from ssh(1)'s getopt string).
SSH_OPTIONS_WITH_VALUE = frozenset("BbcDEeFIiJLlmOopQRSWw")

# ssh-tote flag -> (Options attribute, value it sets)
FLAGS = {
    "--tui": ("interactive", True),
    "--print": ("dry_run", True),
    "--no-env": ("send_env", False),
    "--no-aliases": ("send_aliases", False),
    "--no-dir": ("use_configured_dir", False),
    "--help": ("show_help", True),
    "--version": ("show_version", True),
}
# ssh-tote option taking a value -> Options attribute
VALUE_OPTIONS = {"--dir": "dotfiles_dir", "--shell": "shell"}

USAGE = """\
usage: ssh-tote [ssh-tote options] [ssh options] host [command]
       ssh-tote                      # interactive host + variable picker

ssh-tote options (everything else is passed through to ssh):
  --tui               pick which variables/aliases to send before connecting
  --print             show the generated rcfile and ssh command, don't connect
  --no-env            don't send the variables listed in `env`
  --no-aliases        don't send the aliases listed in `aliases`
  --dir PATH          also ship a dotfiles dir (like sshrc): its bin/ goes on
                      PATH and its .bashrc is sourced; exported as $SSHHOME
  --no-dir            ignore the `dir` setting from the config file
  --shell PATH        local shell to read aliases from (default: $SHELL)
  --help, --version

config: {settings_path}
"""


class UsageError(Exception):
    pass


@dataclass
class Options:
    ssh_args: list = field(default_factory=list)
    host: str | None = None
    command: list = field(default_factory=list)
    interactive: bool = False
    dry_run: bool = False
    send_env: bool = True
    send_aliases: bool = True
    dotfiles_dir: str | None = None
    use_configured_dir: bool = True
    shell: str | None = None
    show_help: bool = False
    show_version: bool = False


def parse_arguments(argv):
    return _ArgumentParser(argv).parse()


class _ArgumentParser:
    def __init__(self, argv):
        self.argv = argv
        self.position = 0
        self.options = Options()

    def parse(self):
        while self._has_next() and self.options.host is None:
            self._parse_argument(self._next())
        self.options.command = self.argv[self.position :]
        return self.options

    def _parse_argument(self, argument):
        option_name = argument.partition("=")[0]
        if argument in FLAGS:
            setattr(self.options, *FLAGS[argument])
        elif option_name in VALUE_OPTIONS:
            self._parse_value_option(argument)
        elif argument == "--":
            self._parse_host_after_separator()
        elif argument.startswith("--"):
            raise UsageError(f"unknown option {argument}")
        elif argument.startswith("-") and argument != "-":
            self._parse_ssh_options(argument)
        else:
            self.options.host = argument

    def _parse_value_option(self, argument):
        name, has_inline_value, value = argument.partition("=")
        if not has_inline_value:
            value = self._require_next(name)
        setattr(self.options, VALUE_OPTIONS[name], value)

    def _parse_host_after_separator(self):
        if self._has_next():
            self.options.host = self._next()

    def _parse_ssh_options(self, argument):
        """Handle ssh's getopt-style bundles such as -v, -p 22, -p22 and -vp 22."""
        self.options.ssh_args.append(argument)
        letters = argument[1:]
        for index, letter in enumerate(letters):
            if letter in SSH_OPTIONS_WITH_VALUE:
                value_is_separate = index == len(letters) - 1
                if value_is_separate:
                    value = self._require_next(f"ssh option -{letter}")
                    self.options.ssh_args.append(value)
                return

    def _require_next(self, option):
        if self._has_next():
            return self._next()
        raise UsageError(f"{option} requires an argument")

    def _has_next(self):
        return self.position < len(self.argv)

    def _next(self):
        argument = self.argv[self.position]
        self.position += 1
        return argument
