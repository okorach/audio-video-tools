#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

"""Backups of the files that the tools modify in place, and their restoration.

A tool that modifies a file keeps the former one as <name>.<kind>.<ext>, kind being before_volume, before_r<angle>,
before_flip_<direction> or before-denoise. The next backups of the same file, whatever the tool, are numbered
<name>.<kind>.2.<ext>, .3... so that the order of the modifications is known and they can be undone in reverse order."""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

import mediatools.utilities as util
from mediatools import log

VOLUME: str = "before_volume"
ROTATE: str = "before_r"  # Followed by the angle
FLIP: str = "before_flip_"  # Followed by the direction
DENOISE: str = "before-denoise"

# The .bak.<n> suffix is the one given by former versions to the backup replaced by a new one of the same name
_NAME_RE: re.Pattern = re.compile(
    r"^(?P<stem>.+)\.(?P<kind>before_volume|before_r-?\d+|before_flip_(?:leftright|topbottom)|before-denoise)"
    r"(?:\.(?P<seq>\d+)|\.bak\.(?P<bak>\d+))?(?P<ext>\.[^.]+)$",
    re.IGNORECASE,
)


class Backup(NamedTuple):
    """A backup file: its position in the history of the modifications of the original file (the higher the more recent), its kind and path"""

    order: tuple[int, int]
    kind: str
    path: str


def is_backup(filename: str) -> bool:
    """Returns True if the name of a file is the one of a backup"""
    return _NAME_RE.match(os.path.basename(filename)) is not None


def find(inputs: list[str]) -> dict[str, list[Backup]]:
    """Returns the backups found for the inputs, as {original file: backups from the oldest to the most recent}: all the backups of the
    input directories (recursively), and for an input file, its backups (all those of its original file if it is a backup)"""
    candidates: list[tuple[str, str | None]] = []  # (file, the only original wanted, None for any)
    for path in inputs:
        path = os.path.abspath(path)
        if os.path.isdir(path):
            candidates += [(os.path.join(folder, name), None) for folder, _, names in os.walk(path) for name in names]
            continue
        folder, name = os.path.split(path)
        if not os.path.isdir(folder):
            continue
        match = _NAME_RE.match(name)
        wanted = os.path.join(folder, match["stem"] + match["ext"]) if match else path
        candidates += [(os.path.join(folder, other), os.path.normcase(wanted)) for other in os.listdir(folder)]
    found: dict[str, set[Backup]] = {}
    for file, wanted in candidates:
        match = _NAME_RE.match(os.path.basename(file))
        if not match:
            continue
        original = os.path.join(os.path.dirname(file), match["stem"] + match["ext"])
        if wanted is None or os.path.normcase(original) == wanted:
            order = (0, int(match["bak"])) if match["bak"] else (int(match["seq"] or 1), 0)
            found.setdefault(original, set()).add(Backup(order, match["kind"].lower(), file))
    return {original: sorted(backups) for original, backups in found.items()}


def next_name(filename: str, kind: str) -> str:
    """Returns the name of the backup to make of a file before modifying it, numbered after all its existing backups (of any kind).
    No existing file has that name"""
    root, extension = os.path.splitext(filename)
    existing = find([filename]).get(os.path.abspath(filename), [])
    seq = max((backup.order[0] for backup in existing), default=0) + 1
    while True:
        name = f"{root}.{kind}{'' if seq == 1 else f'.{seq}'}{extension}"
        if not os.path.exists(name):
            return name
        seq += 1


def expand_inputs(inputs: list[str], input_type: str | tuple[str, ...]) -> list[str]:
    """Replaces the directories of the inputs by the files they contain, leaving out the backups: a tool must not modify them.
    A backup given explicitly as input is kept. Exits with code 1 if there is no input file left"""
    explicit = {os.path.normcase(os.path.abspath(f)) for f in inputs if not os.path.isdir(f)}
    files = util.expand_input_files(inputs, input_type)
    kept = [f for f in files if not is_backup(f) or os.path.normcase(os.path.abspath(f)) in explicit]
    if len(kept) < len(files):
        log.logger.info("Ignoring %d backup file(s)", len(files) - len(kept))
    if not kept:
        log.logger.error("No input file found in %s", ", ".join(inputs))
        sys.exit(1)
    return kept


def add_restore_arg(parser: argparse.ArgumentParser | argparse._MutuallyExclusiveGroup) -> None:
    """Adds the --restore option to the parser (or option group) of a tool that keeps backups"""
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Undo the modifications of this tool: put back the files from their backups (before_...) and remove the modified ones",
    )


def _undo(original: str, history: list[Backup], kind: re.Pattern) -> bool:
    """Replaces a file by its most recent backups, one after the other, as long as they are of the kind to restore.
    Returns False if some backups of that kind could not be restored"""
    history = list(history)
    try:
        while history:
            latest = [backup for backup in history if backup.order == history[-1].order]
            if not any(kind.fullmatch(backup.kind) for backup in latest):
                break
            if len(latest) > 1:
                names = ", ".join(os.path.basename(backup.path) for backup in latest)
                log.logger.error("Can't restore %s: the order of the backups %s is unknown", original, names)
                return False
            Path(latest[0].path).replace(original)  # Removes the modified file and renames the backup in a single step
            history.pop()
    except OSError as e:
        log.logger.error("Could not restore %s: %s", original, e)
        return False
    if any(kind.fullmatch(backup.kind) for backup in history):
        log.logger.error("Can't restore %s further: it was modified afterwards, restore %s first", original, os.path.basename(history[-1].path))
        return False
    log.logger.info("Restored %s", original)
    return True


def restore(inputs: list[str], kind: str, file_filter: object = None) -> None:
    """Undoes, in reverse order, the modifications of the inputs that made backups of a kind (a regular expression).
    file_filter(original file) can exclude files. A modification followed by one of another kind is not undone (the other one must be
    restored first). A file that fails is logged and skipped; the program then exits with code 1 at the end"""
    pattern = re.compile(kind)
    histories = {
        original: history
        for original, history in find(inputs).items()
        if any(pattern.fullmatch(backup.kind) for backup in history) and (file_filter is None or file_filter(original))
    }
    if not histories:
        log.logger.warning("No backup to restore found in %s", ", ".join(inputs))
    progress = util.GlobalProgress(len(histories))
    failed = 0
    # A backup of a backup (made by a former version) is restored first
    for original in sorted(histories, key=lambda f: os.path.basename(f).lower().count(".before"), reverse=True):
        # The files may have changed since the search, when a backup of a backup has been restored
        if not _undo(original, [b for b in histories[original] if os.path.isfile(b.path)], pattern):
            failed += 1
        progress.done()
    log.logger.info("%d file(s) restored", len(histories) - failed)
    if failed:
        log.logger.error("%d file(s) could not be restored", failed)
        sys.exit(1)
