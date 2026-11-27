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

"""Tests of the backups of the files modified in place and of --restore"""

import os
from pathlib import Path
from unittest import mock

import pytest

import mediatools.audio_denoise as dn
from mediatools import backups, tools
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil

ROTATE: str = backups.ROTATE + r"-?\d+"
FLIP: str = backups.FLIP + "[a-z]+"


def modify(file: Path, kind: str, content: str) -> None:
    """Simulates a tool modifying a file: keeps its backup and writes the new content"""
    file.rename(backups.next_name(str(file), kind))
    file.write_text(content)


def contents(folder: Path) -> dict[str, str]:
    """Returns the content of the files of a directory"""
    return {f.name: f.read_text() for f in folder.iterdir()}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a.before_volume.mp3", True),
        ("a.before_volume.2.mp3", True),
        ("a.before_r90.mp4", True),
        ("a.before_r-90.2.mp4", True),
        ("a.before_flip_topbottom.mp4", True),
        ("a.before-denoise.mp3", True),
        ("a.before_r90.bak.000.mp4", True),
        ("a.before_wedding.mp4", False),
        ("before_volume.mp3", False),
        ("a.mp4", False),
    ],
)
def test_is_backup(name: str, expected: bool) -> None:
    """Only the names given by the tools are backups"""
    assert backups.is_backup(name) is expected


def test_next_name_numbers_the_backups_of_all_the_tools(tmp_path: Path) -> None:
    """The backups of a file are numbered in the order of the modifications, whatever the tool"""
    file = tmp_path / "a.mp4"
    file.write_text("v0")
    for i, kind in enumerate(("before_volume", "before_r90", "before_r180", "before_flip_leftright", "before-denoise"), start=1):
        modify(file, kind, f"v{i}")
    assert sorted(contents(tmp_path)) == [
        "a.before-denoise.5.mp4",
        "a.before_flip_leftright.4.mp4",
        "a.before_r180.3.mp4",
        "a.before_r90.2.mp4",
        "a.before_volume.mp4",
        "a.mp4",
    ]


def test_restore_undoes_the_modifications_of_a_tool_in_reverse_order(tmp_path: Path) -> None:
    """Several rotations of different angles are undone from the latest to the first one"""
    file = tmp_path / "a.mp4"
    file.write_text("v0")
    modify(file, "before_r90", "v1")
    modify(file, "before_r180", "v2")
    modify(file, "before_r90", "v3")
    backups.restore([str(tmp_path)], ROTATE)
    assert contents(tmp_path) == {"a.mp4": "v0"}


def test_restore_stops_at_the_modification_of_another_tool(tmp_path: Path) -> None:
    """Only the latest modifications are undone: the ones under another tool's need that tool to be restored first"""
    file = tmp_path / "a.mp4"
    file.write_text("v0")
    modify(file, "before_r90", "v1")
    modify(file, "before_flip_leftright", "v2")
    modify(file, "before_r90", "v3")
    with pytest.raises(SystemExit) as e:
        backups.restore([str(file)], ROTATE)
    assert e.value.code == 1
    assert file.read_text() == "v2"
    with pytest.raises(SystemExit):  # The flip is now the latest modification
        backups.restore([str(file)], ROTATE)
    assert file.read_text() == "v2"
    backups.restore([str(file)], FLIP)
    assert file.read_text() == "v1"
    backups.restore([str(file)], ROTATE)
    assert contents(tmp_path) == {"a.mp4": "v0"}


def test_restore_ignores_the_files_modified_by_other_tools(tmp_path: Path) -> None:
    """A file that has no backup of the tool is left alone, without error"""
    file = tmp_path / "a.mp4"
    file.write_text("v0")
    modify(file, "before_volume", "v1")
    backups.restore([str(tmp_path)], ROTATE)
    assert contents(tmp_path) == {"a.mp4": "v1", "a.before_volume.mp4": "v0"}


def test_restore_the_backups_of_former_versions(tmp_path: Path) -> None:
    """The former .bak.<n> backups are older than the backup without number, from .bak.000 (the oldest)"""
    for name, content in (("a.mp4", "v3"), ("a.before_r90.mp4", "v2"), ("a.before_r90.bak.001.mp4", "v1"), ("a.before_r90.bak.000.mp4", "v0")):
        (tmp_path / name).write_text(content)
    backups.restore([str(tmp_path / "a.before_r90.mp4")], ROTATE)
    assert contents(tmp_path) == {"a.mp4": "v0"}


def test_restore_refuses_an_unknown_order(tmp_path: Path) -> None:
    """2 former backups without number can't be ordered: nothing is changed"""
    for name in ("a.mp4", "a.before_r90.mp4", "a.before_r180.mp4"):
        (tmp_path / name).write_text(name)
    with pytest.raises(SystemExit):
        backups.restore([str(tmp_path)], ROTATE)
    assert sorted(contents(tmp_path)) == ["a.before_r180.mp4", "a.before_r90.mp4", "a.mp4"]


def test_restore_logs_a_failure_and_carries_on(tmp_path: Path) -> None:
    """A file that can't be restored doesn't stop the others"""
    for name in ("a", "b"):
        (tmp_path / f"{name}.mp4").write_text("v1")
        (tmp_path / f"{name}.before_r90.mp4").write_text("v0")
    replace = Path.replace

    def failing(source: Path, target: str) -> None:
        """Fails on a"""
        if source.name.startswith("a."):
            raise PermissionError("locked")
        replace(source, target)

    with mock.patch.object(Path, "replace", autospec=True, side_effect=failing), pytest.raises(SystemExit):
        backups.restore([str(tmp_path)], ROTATE)
    assert (tmp_path / "b.mp4").read_text() == "v0"
    assert (tmp_path / "a.before_r90.mp4").exists()


def test_expand_inputs_leaves_out_the_backups_of_the_directories(tmp_path: Path) -> None:
    """The backups found in a directory are not processed, the ones given explicitly are"""
    for name in ("a.mp4", "a.before_r90.mp4"):
        (tmp_path / name).write_text("x")
    video_type = fil.FileType.VIDEO_FILE
    assert [os.path.basename(f) for f in backups.expand_inputs([str(tmp_path)], video_type)] == ["a.mp4"]
    explicit = str(tmp_path / "a.before_r90.mp4")
    assert backups.expand_inputs([explicit], video_type) == [explicit]


def test_expand_inputs_with_only_backups(tmp_path: Path) -> None:
    """Exit when there is nothing left to process"""
    (tmp_path / "a.before_r90.mp4").write_text("x")
    with pytest.raises(SystemExit):
        backups.expand_inputs([str(tmp_path)], fil.FileType.VIDEO_FILE)


@pytest.mark.parametrize(
    ("command", "action", "kind"),
    [
        (tools.videotool, "rotate", "before_r270"),
        (tools.videotool, "flip", "before_flip_topbottom"),
        (tools.videotool, "volume", "before_volume"),
        (tools.audiotool, "denoise", "before-denoise"),
        (tools.audiotool, "volume", "before_volume"),
    ],
)
def test_restore_command_of_the_tools(tmp_path: Path, command: object, action: str, kind: str) -> None:
    """Each tool that keeps backups restores them with --restore, without running ffmpeg"""
    extension = "mp3" if command is tools.audiotool else "mp4"
    file = tmp_path / f"a.{extension}"
    file.write_text("v0")
    modify(file, kind, "v1")
    argv = ["tool", action, "-i", str(tmp_path), "--restore"]
    with mock.patch("sys.argv", argv), mock.patch.object(util, "run_ffmpeg") as ffmpeg:
        try:
            command()
        except SystemExit as e:
            assert e.code == 0
    ffmpeg.assert_not_called()
    assert contents(tmp_path) == {f"a.{extension}": "v0"}


def test_denoise_refuses_a_second_time_and_numbers_after_the_other_backups(tmp_path: Path) -> None:
    """A denoise backup is numbered after the backups of the other tools, and a denoised file is not denoised again"""
    file = tmp_path / "a.mp3"
    file.write_text("v0")
    modify(file, "before_volume", "v1")
    assert dn.backup_file(str(file)) == str(tmp_path / "a.before-denoise.2.mp3")
    modify(file, "before-denoise", "v2")
    with pytest.raises(ValueError, match="already denoised"):
        dn.denoise(str(file), keep_name=True)


def test_rotate_keep_name_twice_then_restore(short_video: str, tmp_path: Path) -> None:
    """Real ffmpeg: 2 rotations keeping the name, then --restore gives the original file back"""
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(Path(short_video).read_bytes())
    original = clip.read_bytes()
    for angle in (90, 180):
        video.rotate(str(clip), angle=angle, keep_name=True, hw_accel="off")
    assert sorted(f.name for f in tmp_path.iterdir()) == ["clip.before_r180.2.mp4", "clip.before_r90.mp4", "clip.mp4"]
    backups.restore([str(tmp_path)], ROTATE)
    assert [f.name for f in tmp_path.iterdir()] == ["clip.mp4"]
    assert clip.read_bytes() == original
