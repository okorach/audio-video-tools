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

"""Tests of the -v/--verbosity option and of the creation of the log files"""

import argparse
import contextlib
import importlib
import logging
import os
import pathlib
import subprocess
import sys
from unittest.mock import patch
import pytest
import mediatools.utilities as util


@pytest.mark.parametrize(
    "value,expected",
    [("CRITICAL", 0), ("ERROR", 1), ("WARNING", 2), ("INFO", 3), ("DEBUG", 4), ("debug", 4), ("Info", 3), (None, 3), ("", 3), ("4", 4), (2, 2)],
)
def test_parse_verbosity(value, expected):
    assert util.parse_verbosity(value) == expected


def test_parse_verbosity_invalid():
    with pytest.raises(ValueError):
        util.parse_verbosity("LOUD")


def parse(*args) -> dict:
    p = argparse.ArgumentParser()
    util.add_verbosity_arg(p)
    return vars(p.parse_args(args))


def test_verbosity_option():
    assert util.get_verbosity(parse()) == 3
    assert util.get_verbosity(parse("-v", "DEBUG")) == 4
    assert util.get_verbosity(parse("--verbosity", "warning")) == 2


def test_deprecated_debug_option():
    assert util.get_verbosity(parse("-g", "4")) == 4
    assert util.get_verbosity(parse("-g", "debug")) == 4


def test_invalid_verbosity_option():
    with pytest.raises(SystemExit):
        parse("-v", "LOUD")


def test_set_debug_level_accepts_names():
    util.set_debug_level("DEBUG")
    assert util.log.logger.level == logging.DEBUG
    util.set_debug_level("error")
    assert util.log.logger.level == logging.ERROR
    util.set_debug_level(None)
    assert util.log.logger.level == logging.INFO


def test_parse_media_args_verbosity():
    p = util.get_common_args("test-verbosity", "test")
    kwargs = util.parse_media_args(p, ["-i", "it/song.mp3", "-v", "DEBUG"])
    assert "verbosity" not in kwargs
    assert util.DEBUG_LEVEL == 4
    util.set_debug_level(None)


def test_no_empty_log_file(tmp_path):
    """Importing mediatools doesn't create mediatools.log, only the log file of the tool is created"""
    code = "import mediatools.utilities as util; util.init('my-tool'); util.log.logger.info('hello')"
    env = {**os.environ, "PYTHONPATH": str(pathlib.Path(__file__).parent.parent)}
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, check=True, capture_output=True, env=env)
    assert sorted(f.name for f in tmp_path.iterdir()) == ["my-tool.log"]


TOOLS = (
    "cli.shuffle",
    "mediatools.album_art",
    "mediatools.audio_normalize",
    "mediatools.audioconcat",
    "mediatools.concat",
    "mediatools.datefixer",
    "mediatools.encodeauto",
    "mediatools.filespecs",
    "mediatools.fix_mp3_meta",
    "mediatools.linker",
    "mediatools.mux",
    "mediatools.poster",
    "mediatools.renamer",
    "mediatools.slideshow",
    "mediatools.stack",
)


@pytest.mark.parametrize("module", TOOLS)
def test_tools_have_the_verbosity_option(module, capsys):
    with patch.object(sys, "argv", [module, "-h"]), pytest.raises(SystemExit) as e:
        importlib.import_module(module).main()
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert "--verbosity" in out
    assert "--debug" not in out  # The former option is hidden


@pytest.mark.parametrize("module", TOOLS)
def test_tools_reject_an_invalid_verbosity(module):
    with patch.object(sys, "argv", [module, "-v", "LOUD"]), pytest.raises(SystemExit) as e:
        importlib.import_module(module).main()
    assert e.value.code == 2


@pytest.mark.parametrize("module", ("mediatools.audio_lib", "mediatools.audio_list"))
@pytest.mark.parametrize("option", ("-v", "--verbosity", "-g"))
def test_directory_tools_verbosity(module, option, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # audio-list writes music.csv in the current folder
    with patch.object(sys, "argv", [module, option, "DEBUG", str(tmp_path)]), contextlib.suppress(SystemExit):
        importlib.import_module(module).main()
    assert util.DEBUG_LEVEL == 4
    util.set_debug_level(None)


def test_normalize_sets_the_verbosity(tmp_path):
    with patch.object(sys, "argv", ["audio-normalize", "-v", "WARNING", "-i", str(tmp_path)]), contextlib.suppress(SystemExit):
        importlib.import_module("mediatools.audio_normalize").main()
    assert util.DEBUG_LEVEL == 2
    util.set_debug_level(None)


def test_add_input_and_output_args():
    p = argparse.ArgumentParser()
    util.add_input_args(p, "inputs")
    util.add_output_args(p, "output")
    assert vars(p.parse_args(["-i", "a", "b", "-o", "c"])) == {"inputfiles": ["a", "b"], "outputfile": "c"}
    assert vars(p.parse_args(["--inputfiles", "a"])) == {"inputfiles": ["a"], "outputfile": None}
    with pytest.raises(SystemExit):
        p.parse_args(["-o", "c"])  # -i is required by default


def test_add_input_args_optional_with_aliases():
    p = argparse.ArgumentParser()
    util.add_input_args(p, "inputs", required=False, dest="files", aliases=("-f", "--files"))
    assert vars(p.parse_args([])) == {"files": None}
    assert vars(p.parse_args(["-f", "a"])) == {"files": ["a"]}
    assert vars(p.parse_args(["--files", "a", "b"])) == {"files": ["a", "b"]}


def test_add_output_args_required():
    p = argparse.ArgumentParser()
    util.add_output_args(p, "output", required=True)
    with pytest.raises(SystemExit):
        p.parse_args([])


# album_art has positional inputs and linker works on a directory (-d)
@pytest.mark.parametrize("module", [m for m in TOOLS if m not in ("mediatools.album_art", "mediatools.linker")])
def test_tools_document_the_input_option(module, capsys):
    with patch.object(sys, "argv", [module, "-h"]), pytest.raises(SystemExit):
        importlib.import_module(module).main()
    assert "--inputfiles" in capsys.readouterr().out
