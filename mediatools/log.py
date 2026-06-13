#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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

import os
import sys
import logging
import pathlib


class _Utf8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            try:
                msg = self.format(record) + self.terminator
                if hasattr(self.stream, "buffer"):
                    self.stream.buffer.write(msg.encode("utf-8", errors="replace"))
                    self.stream.buffer.flush()
                else:
                    enc = getattr(self.stream, "encoding", "utf-8") or "utf-8"
                    self.stream.write(msg.encode(enc, errors="replace").decode(enc))
                    self.flush()
            except Exception:
                self.handleError(record)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


logger: logging.Logger = logging.getLogger("mediatools")
formatter: logging.Formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)-7s | %(threadName)-15s | %(message)s")
try:
    fh: logging.FileHandler = logging.FileHandler("mediatools.log", encoding="utf-8")
except PermissionError:
    fallback_log = pathlib.Path(os.getenv("TMP", "/")) / "mediatools.log"
    fh = logging.FileHandler(fallback_log, encoding="utf-8")

# fh.setLevel(logging.DEBUG)
ch: logging.StreamHandler = _Utf8StreamHandler()
# ch.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.addHandler(ch)
fh.setFormatter(formatter)
ch.setFormatter(formatter)


def set_logger(name: str) -> None:
    global logger
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False
    try:
        new_fh = logging.FileHandler(name + ".log", encoding="utf-8")
    except PermissionError:
        _fallback_log = pathlib.Path(os.getenv("TMP", "/")) / (name + ".log")
        new_fh = logging.FileHandler(_fallback_log, encoding="utf-8")
    new_ch = _Utf8StreamHandler()
    logger.addHandler(new_fh)
    logger.addHandler(new_ch)
    new_fh.setFormatter(formatter)
    new_ch.setFormatter(formatter)


def get_logging_level(intlevel: int) -> int:
    if intlevel >= 4:
        lvl = logging.DEBUG
    elif intlevel >= 3:
        lvl = logging.INFO
    elif intlevel >= 2:
        lvl = logging.WARNING
    elif intlevel >= 1:
        lvl = logging.ERROR
    else:
        lvl = logging.CRITICAL
    return lvl
