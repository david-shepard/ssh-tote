#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""ssh-tote - ssh to a host, bringing your local aliases and environment along.

Run `ssh-tote --help` for usage. The code lives in the sshtotelib package next
to this file.
"""

import sys
from pathlib import Path

# Resolve symlinks (e.g. ~/bin/ssh-tote) so the package beside the real file is found.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sshtotelib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
