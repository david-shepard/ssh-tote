"""Hosts offered by the picker: recently used ones, then ~/.ssh/config."""

import glob
import os
import re
from dataclasses import dataclass
from pathlib import Path

HISTORY_LIMIT = 50
CONFIG_LINE = re.compile(r"\s*(\w+)\s*(?:=|\s)\s*(.*)")
PATTERN_CHARS = frozenset("*?!")


@dataclass(frozen=True)
class HostChoice:
    name: str
    source: str


class History:
    def __init__(self, path):
        self.path = path

    def hosts(self):
        try:
            lines = self.path.read_text().splitlines()
        except OSError:
            return []
        return [line for line in lines if line.strip()]

    def record(self, host):
        """Move host to the front. Failing to write history never stops a login."""
        hosts = [host] + [known for known in self.hosts() if known != host]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("\n".join(hosts[:HISTORY_LIMIT]) + "\n")
        except OSError:
            pass


def host_choices(history, ssh_config_path):
    choices = []
    seen = set()
    sources = (
        ("recent", history.hosts()),
        ("ssh config", ssh_config_hosts(ssh_config_path)),
    )
    for source, hosts in sources:
        for host in hosts:
            if host not in seen:
                seen.add(host)
                choices.append(HostChoice(host, source))
    return choices


def ssh_config_hosts(config_path):
    """Concrete `Host` names, following `Include`. Patterns are skipped."""
    config_path = Path(config_path).expanduser()
    return _read_ssh_config(config_path, config_path.parent, visited=set())


def _read_ssh_config(path, ssh_dir, visited):
    if path in visited:
        return []
    visited.add(path)
    hosts = []
    for keyword, value in _config_entries(path):
        if keyword == "host":
            hosts += [name for name in value.split() if PATTERN_CHARS.isdisjoint(name)]
        elif keyword == "include":
            for included in _included_paths(value, ssh_dir):
                hosts += _read_ssh_config(included, ssh_dir, visited)
    return hosts


def _config_entries(path):
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return []
    matches = [CONFIG_LINE.match(line) for line in lines if not _is_comment(line)]
    return [(m.group(1).lower(), m.group(2).strip()) for m in matches if m]


def _is_comment(line):
    return line.lstrip().startswith("#")


def _included_paths(value, ssh_dir):
    """ssh resolves relative Include paths against ~/.ssh."""
    for pattern in value.split():
        pattern = os.path.join(ssh_dir, os.path.expanduser(pattern))
        yield from (Path(path) for path in sorted(glob.glob(pattern)))
