"""The one-line command that unpacks the payload on the server and starts a shell."""

from dataclasses import dataclass

# Linux caps a single argv string at 128 KiB (MAX_ARG_STRLEN), and the remote
# shell receives the whole bootstrap as one argument.
MAX_BOOTSTRAP_BYTES = 120_000
KILOBYTE = 1024

# Warning: the steps are joined into one line and wrapped in `sh -c '...'`
# for the user's login shell, which may be bash, zsh, dash, fish or tcsh. They
# must not contain single quotes, `\\`, `\'`, `!` or newlines.
PREPARE_STEPS = (
    "d=$(mktemp -d /dev/shm/.ssh-tote.XXXXXX 2>/dev/null"
    ' || mktemp -d "${TMPDIR:-/tmp}/.ssh-tote.XXXXXX") || exit 1',
    'trap "rm -rf \\"$d\\"" EXIT HUP INT TERM',
    'if base64 -d </dev/null >/dev/null 2>&1; then b="base64 -d";'
    ' else b="base64 -D"; fi',
)
# Hand over to the start script so the payload leaves the process list: any
# user on the server can read a process's command line, and this one holds
# every variable we send.
START_STEP = 'exec sh "$d/start" "$d"'

# Shipped in the payload and run by START_STEP with the temp dir as $1.
START_NAME = "start"
START_SCRIPT = """\
export SSH_TOTE_HOME="$1"
trap 'rm -rf "$SSH_TOTE_HOME"' EXIT HUP INT TERM
if command -v bash >/dev/null 2>&1; then
  bash --rcfile "$SSH_TOTE_HOME/rc" -i
else
  ENV="$SSH_TOTE_HOME/rc" sh -i
fi
"""


@dataclass(frozen=True)
class Bootstrap:
    command: str

    @classmethod
    def for_payload(cls, encoded_payload):
        unpack = f'echo {encoded_payload} | $b | tar xzf - -C "$d" || exit 1'
        script = "; ".join([*PREPARE_STEPS, unpack, START_STEP])
        assert "'" not in script, "would break the sh -c '...' wrapper"
        return cls(f"sh -c '{script}'")

    @property
    def size(self):
        return len(self.command)

    @property
    def too_large(self):
        return self.size > MAX_BOOTSTRAP_BYTES


def human_size(size):
    if size < KILOBYTE:
        return f"{size} B"
    return f"{size / KILOBYTE:.1f} KB"
