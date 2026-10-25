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

"""Tests of the unified commands videotool, audiotool, imagetool and pdftool"""

import re
import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import tools

ROOT = Path(__file__).resolve().parent.parent
# The tools that are not about video, audio, images or PDF only
NOT_UNIFIED = {"linker", "renamer", "datefixer", "shuffle"}


def console_scripts() -> dict[str, str]:
    """Returns the console scripts of pyproject.toml: their names and the functions they run"""
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    section = content.split("[project.scripts]")[1].split("[build-system]")[0]
    return dict(re.findall(r'^([\w-]+)\s*=\s*"([^"]+)"', section, re.MULTILINE))


@pytest.mark.parametrize(("command", "action"), [(c, a) for c, actions in tools.COMMANDS.items() for a in actions])
def test_every_action_is_implemented(command: str, action: str) -> None:
    """Every action is implemented"""
    assert callable(tools.get_action_function(command, action))


def test_only_the_unified_commands_and_the_generic_tools_are_console_scripts() -> None:
    """Only the unified commands and the generic tools are console scripts"""
    assert set(console_scripts()) == set(tools.COMMANDS) | NOT_UNIFIED


def test_commands_are_registered(request: pytest.FixtureRequest) -> None:
    """Commands are registered"""
    scripts = console_scripts()
    setup_py = (ROOT / "setup.py").read_text(encoding="utf-8")
    for command in tools.COMMANDS:
        assert scripts[command] == f"mediatools.tools:{command}"
        assert f'"{command} = mediatools.tools:{command}"' in setup_py


def test_run_passes_the_parameters_to_the_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run passes the parameters to the action"""
    action = mock.Mock(side_effect=lambda: seen.extend(sys.argv))
    seen: list[str] = []
    monkeypatch.setattr(tools, "get_action_function", lambda _command, _action: action)
    monkeypatch.setattr(sys, "argv", ["videotool"])
    tools.run("videotool", ["crop", "-i", "a.mp4", "--box", "1920x1080", "--center"])
    action.assert_called_once()
    assert seen == ["videotool crop", "-i", "a.mp4", "--box", "1920x1080", "--center"]


def test_run_uses_the_command_line_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run uses the command line by default"""
    seen: list[str] = []
    monkeypatch.setattr(tools, "get_action_function", lambda _command, _action: lambda: seen.extend(sys.argv))
    monkeypatch.setattr(sys, "argv", ["pdftool", "split", "-i", "a.pdf"])
    tools.pdftool()
    assert seen == ["pdftool split", "-i", "a.pdf"]


def test_run_unknown_action(capsys: pytest.CaptureFixture[str]) -> None:
    """Run unknown action"""
    with pytest.raises(SystemExit) as e:
        tools.run("videotool", ["snpa"])
    assert e.value.code == 2
    assert "unknown action 'snpa', did you mean 'snap'?" in capsys.readouterr().err


def test_run_without_action(capsys: pytest.CaptureFixture[str]) -> None:
    """Run without action"""
    with pytest.raises(SystemExit) as e:
        tools.run("audiotool", [])
    assert e.value.code == 2
    assert "denoise" in capsys.readouterr().out


@pytest.mark.parametrize("option", ["-h", "--help"])
def test_run_help(option: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Run help"""
    with pytest.raises(SystemExit) as e:
        tools.run("imagetool", [option])
    assert e.value.code == 0
    assert "usage: imagetool <action>" in capsys.readouterr().out


def test_action_help_shows_the_unified_command(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Action help shows the unified command"""
    # Python 3.14 names the program "python -m pytest" when run as a module, console scripts are named after sys.argv[0]
    monkeypatch.setattr(sys.modules["__main__"], "__spec__", None)
    with pytest.raises(SystemExit) as e:
        tools.run("videotool", ["snap", "-h"])
    assert e.value.code == 0
    assert "usage: videotool snap" in capsys.readouterr().out


def test_videotool_snap_end_to_end(video_5s: str, tmp_path: Path) -> None:
    """Videotool snap end to end"""
    video = tmp_path / "clip.mp4"
    video.write_bytes(Path(video_5s).read_bytes())
    tools.run("videotool", ["snap", "-i", str(video), "--nbr_photos", "2"])
    assert sorted(p.name for p in tmp_path.glob("*.jpg")) == ["clip.1.jpg", "clip.2.jpg"]
