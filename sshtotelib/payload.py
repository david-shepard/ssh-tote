"""The archive that carries the rcfile (and optional dotfiles) to the server."""

import base64
import io
import re
import tarfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from .bootstrap import MAX_BOOTSTRAP_BYTES, START_NAME, START_SCRIPT

RCFILE_NAME = "rc"
DOTFILES_NAME = "dir"
RCFILE_MODE = 0o600
# Same files the original sshrc leaves behind.
SKIPPED_DOTFILES = re.compile(r"^(\.git|README|LICENSE|ssh-tote$)")
# Compressed size past which the base64 (4/3 larger) can't fit the bootstrap.
MAX_COMPRESSED_BYTES = MAX_BOOTSTRAP_BYTES * 3 // 4


@dataclass(frozen=True)
class Payload:
    rcfile: str
    dotfiles_dir: Path | None = None

    def encode(self, warn=lambda message: None):
        """Base64 of a tar.gz holding `rc`, `start` and any dotfiles as `dir/`.

        warn(message) hears about every symlink left out of the dotfiles.
        """
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            _add_text(archive, RCFILE_NAME, self.rcfile)
            _add_text(archive, START_NAME, START_SCRIPT)
            if self.dotfiles_dir:
                _add_dotfiles(archive, self.dotfiles_dir, buffer, warn)
        return base64.b64encode(buffer.getvalue()).decode()


def _add_text(archive, name, text):
    data = text.encode()
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = RCFILE_MODE
    archive.addfile(info, io.BytesIO(data))


def _add_dotfiles(archive, directory, buffer, warn):
    def keep(info):
        if info.issym():
            name = info.name.removeprefix(f"{DOTFILES_NAME}/")
            warn(
                f"not sending {name} -> {info.linkname}: "
                "symlinks aren't supported in a dotfiles dir"
            )
            return None
        # The bootstrap will be refused anyway; don't read a huge dir to the end.
        if _compressed_size(archive, buffer) > MAX_COMPRESSED_BYTES:
            return None
        return info

    for entry in sorted(directory.iterdir()):
        if not SKIPPED_DOTFILES.match(entry.name):
            arcname = f"{DOTFILES_NAME}/{entry.name}"
            archive.add(str(entry), arcname=arcname, filter=keep)


def _compressed_size(archive, buffer):
    """How much compressed output the archive has produced so far.

    Since Python 3.14 gzip holds back about 500 kB of input before compressing
    it. Z_NO_FLUSH hands that input to the compressor without ending the
    deflate block, so unlike the default flush it costs no compression.
    """
    archive.fileobj.flush(zlib.Z_NO_FLUSH)
    return buffer.tell()
