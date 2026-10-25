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

"""Tests of the -i option of the tools: a list of files and/or directories (directories being expanded recursively)"""

import argparse
import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import (
    audio_denoise,
    audio_normalize,
    audiospeed,
    blindify,
    crop,
    crop_ratio,
    datefixer,
    deshake,
    fix_mp3_meta,
    metadata,
    rescale,
    renamer,
    reverse,
    shake,
    speed,
    tools,
    volume,
)
import mediatools.utilities as util
import utilities.file as fil
from types import ModuleType


def _tree(root: Path) -> dict:
    """root/
    a.mp4, c.mp3, notes.txt, pic.jpg
    dir1/ b.mp4, z.mp4, readme.md, sub/ d.mp4, e.pdf
    empty/
    """
    files = {}
    for name in ("a.mp4", "c.mp3", "notes.txt", "pic.jpg", "dir1/b.mp4", "dir1/z.mp4", "dir1/readme.md", "dir1/sub/d.mp4", "dir1/sub/e.pdf"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
        files[name] = str(path)
    (root / "empty").mkdir()
    files["dir1"] = str(root / "dir1")
    files["empty"] = str(root / "empty")
    return files


def _argv(module: ModuleType, *args: str) -> list[str]:
    """The command line of a tool: the unified command and action, or the name of the tool if it has none"""
    action = tools.find_action(module.__name__)
    return [*action, *args] if action else [module.__name__, *args]


def _call_main(module: ModuleType) -> None:
    """Runs a tool the way its command line does: through the unified command if it has one"""
    action = tools.find_action(module.__name__)
    if action:
        tools.run(action[0])
    else:
        module.main()


def _main_exit_ok(module: ModuleType) -> None:
    """Runs a tool, tolerating an exit with code 0"""
    try:
        _call_main(module)
    except SystemExit as e:
        assert e.code in (0, None)


def _names(files: list[str], root: Path) -> list[str]:
    """Returns the paths of the files relative to a root, with / separators"""
    return [Path(f).relative_to(root).as_posix() for f in files]


def test_expand_inputs_files_only(tmp_path: Path) -> None:
    """Files are kept as they are, in the order given, even if they don't exist or are not media files"""
    files = _tree(tmp_path)
    given = [files["c.mp3"], files["a.mp4"], files["notes.txt"], str(tmp_path / "missing.mp4")]
    assert fil.expand_inputs(given) == given


def test_expand_inputs_directory(tmp_path: Path) -> None:
    """A directory is replaced by the media files it contains, recursively, in alphabetical order"""
    files = _tree(tmp_path)
    assert _names(fil.expand_inputs([files["dir1"]]), tmp_path) == ["dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4"]


def test_expand_inputs_files_and_directories(tmp_path: Path) -> None:
    """-i file1.mp4 file2.mp4 dir1: the files and all the files of dir1"""
    files = _tree(tmp_path)
    expanded = fil.expand_inputs([files["c.mp3"], files["a.mp4"], files["dir1"]])
    assert _names(expanded, tmp_path) == ["c.mp3", "a.mp4", "dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4"]


def test_expand_inputs_file_type(tmp_path: Path) -> None:
    """Only the files of the requested types are taken from the directories, not from the arguments"""
    files = _tree(tmp_path)
    assert _names(fil.expand_inputs([str(tmp_path)], fil.FileType.IMAGE_FILE), tmp_path) == ["pic.jpg"]
    assert _names(fil.expand_inputs([str(tmp_path)], (fil.FileType.AUDIO_FILE, fil.FileType.IMAGE_FILE)), tmp_path) == ["c.mp3", "pic.jpg"]
    assert fil.expand_inputs([files["notes.txt"]], fil.FileType.VIDEO_FILE) == [files["notes.txt"]]


def test_expand_inputs_extensions(tmp_path: Path) -> None:
    """Extensions replace the file types"""
    _tree(tmp_path)
    assert _names(fil.expand_inputs([str(tmp_path)], extensions=("pdf",)), tmp_path) == ["dir1/sub/e.pdf"]


def test_expand_inputs_empty_directory(tmp_path: Path) -> None:
    """A directory without matching file gives nothing"""
    files = _tree(tmp_path)
    assert not fil.expand_inputs([files["empty"]])


def test_expand_inputs_keeps_duplicates(tmp_path: Path) -> None:
    """A file given twice is returned twice (concatenating a video with itself is legitimate)"""
    files = _tree(tmp_path)
    assert fil.expand_inputs([files["a.mp4"], files["a.mp4"]]) == [files["a.mp4"]] * 2


def test_expand_input_files_nothing_found(tmp_path: Path) -> None:
    """No input file at all is an error"""
    files = _tree(tmp_path)
    with pytest.raises(SystemExit) as e:
        util.expand_input_files([files["empty"]])
    assert e.value.code == 1


def test_parse_media_args_expands_inputs(tmp_path: Path) -> None:
    """parse_media_args expands the directories of the -i option"""
    files = _tree(tmp_path)
    parser = util.get_common_args("test", "test")
    kwargs = util.parse_media_args(parser, ["-i", files["a.mp4"], files["dir1"]], input_type=fil.FileType.VIDEO_FILE)
    assert _names(kwargs["inputfiles"], tmp_path) == ["a.mp4", "dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4"]


def test_parse_media_args_default_type_is_media(tmp_path: Path) -> None:
    """Without input type all the audio, video and image files of the directories are taken"""
    files = _tree(tmp_path)
    parser = util.get_common_args("test", "test")
    kwargs = util.parse_media_args(parser, ["-i", str(tmp_path)])
    assert _names(kwargs["inputfiles"], tmp_path) == ["a.mp4", "c.mp3", "dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4", "pic.jpg"]
    assert files["notes.txt"] not in kwargs["inputfiles"]


def test_process_input_files() -> None:
    """The function is called on each input file with a copy of the other options"""
    calls = []

    def process(input_file: str, options: dict) -> None:
        """Records the file and the options it is called with"""
        options["modified"] = True
        calls.append((input_file, sorted(options)))

    kwargs = {"inputfiles": ["a", "b"], "level": 3}
    util.process_input_files(kwargs, process)
    assert calls == [("a", ["level", "modified"]), ("b", ["level", "modified"])]
    assert kwargs == {"inputfiles": ["a", "b"], "level": 3}


def test_process_input_files_output_with_several_inputs() -> None:
    """-o with several input files exits with code 2, without processing anything"""
    process = mock.Mock()
    with pytest.raises(SystemExit) as e:
        util.process_input_files({"inputfiles": ["a", "b"], "outputfile": "o"}, process)
    assert e.value.code == 2
    process.assert_not_called()


def test_process_input_files_output_with_one_input() -> None:
    """-o is fine with a single input file"""
    process = mock.Mock()
    util.process_input_files({"inputfiles": ["a"], "outputfile": "o"}, process)
    process.assert_called_once_with("a", {"outputfile": "o"})


def test_process_input_files_failure() -> None:
    """A failing file doesn't prevent the others from being processed, the exit code is 1"""
    seen = []

    def process(input_file: str, options: dict) -> None:
        """Records the file and fails for the file b"""
        seen.append(input_file)
        if input_file == "b":
            raise ValueError("boom")

    with pytest.raises(SystemExit) as e:
        util.process_input_files({"inputfiles": ["a", "b", "c"]}, process)
    assert e.value.code == 1
    assert seen == ["a", "b", "c"]


# Tools processing each input file: (module, patched function or class, extra arguments, type of input files)
VIDEO_TOOLS = [
    (volume, "mediatools.videofile.volume", ["--volume", "200%"]),
    (reverse, "mediatools.videofile.reverse", []),
    (speed, "mediatools.videofile.speed", ["--speed", "2x"]),
    (deshake, "mediatools.videofile.deshake", []),
    (crop, "mediatools.creator.file", ["--box", "10x10"]),
]
IMAGE_TOOLS = [
    (blindify, "mediatools.imagefile.ImageFile", []),
    (shake, "mediatools.imagefile.ImageFile", []),
    (rescale, "mediatools.imagefile.ImageFile", ["--width", "100"]),
    (crop_ratio, "mediatools.imagefile.ImageFile", ["--ratio", "1.5"]),
]


def _run_tool(module: ModuleType, argv: list[str]) -> None:
    """Runs the main function of a tool with the arguments given"""
    with mock.patch.object(sys, "argv", _argv(module, *argv)):
        try:
            _call_main(module)
        except SystemExit as e:
            assert e.code in (0, None)


def _called_files(target: mock.Mock) -> list[str]:
    """The input files the tool was called with (first argument, or filename/input_file keyword)"""
    return [call.args[0] if call.args else call.kwargs.get("filename") for call in target.call_args_list]


@pytest.mark.parametrize(("module", "target", "extra"), VIDEO_TOOLS, ids=[t[0].__name__ for t in VIDEO_TOOLS])
def test_video_tools_process_all_inputs(tmp_path: Path, module: ModuleType, target: str, extra: list) -> None:
    """-i file1.mp4 file2.mp4 dir1 processes file1.mp4, file2.mp4 and all the video files of dir1 (recursively)"""
    files = _tree(tmp_path)
    argv = ["-i", files["a.mp4"], files["dir1/z.mp4"], files["dir1"], *extra]
    with mock.patch(target, return_value=mock.MagicMock() if module is crop else "out.mp4") as patched:
        _run_tool(module, argv)
    if module is crop:
        # creator.file(f).crop(...): the files are the arguments of creator.file
        called = [c.args[0] for c in patched.call_args_list]
    else:
        called = _called_files(patched)
    assert _names(called, tmp_path) == ["a.mp4", "dir1/z.mp4", "dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4"]


@pytest.mark.parametrize(("module", "target", "extra"), IMAGE_TOOLS, ids=[t[0].__name__ for t in IMAGE_TOOLS])
def test_image_tools_process_all_inputs(tmp_path: Path, module: ModuleType, target: str, extra: list) -> None:
    """The image tools process the image files of the directories only"""
    files = _tree(tmp_path)
    (tmp_path / "dir1" / "x.jpg").write_bytes(b"x")
    with mock.patch(target) as image_class:
        _run_tool(module, ["-i", files["pic.jpg"], files["dir1"], *extra])
    assert _names([c.args[0] for c in image_class.call_args_list], tmp_path) == ["pic.jpg", "dir1/x.jpg"]


def test_metadata_processes_all_inputs(tmp_path: Path) -> None:
    """video-metadata processes all the video files of the directories"""
    files = _tree(tmp_path)
    instances = []

    def new_video(filename: str) -> mock.Mock:
        """Records the file and returns a mock of the video"""
        instances.append(filename)
        return mock.Mock()

    with mock.patch("mediatools.videofile.VideoFile", side_effect=new_video):
        _run_tool(metadata, ["-i", files["dir1"], "--author", "me"])
    assert _names(instances, tmp_path) == ["dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4"]


def test_audiospeed_processes_all_inputs(tmp_path: Path) -> None:
    """audio-speed processes the audio files of the directories only"""
    files = _tree(tmp_path)
    (tmp_path / "dir1" / "song.mp3").write_bytes(b"x")
    with mock.patch("mediatools.audiospeed.speed", return_value="out.mp3") as patched:
        _run_tool(audiospeed, ["-i", files["c.mp3"], files["dir1"], "--size", "90"])
    assert _names([c.args[0] for c in patched.call_args_list], tmp_path) == ["c.mp3", "dir1/song.mp3"]


def test_audio_denoise_processes_audio_and_video(tmp_path: Path) -> None:
    """audio-denoise processes the audio and video files of the directories"""
    files = _tree(tmp_path)
    with mock.patch("mediatools.audio_denoise.denoise", return_value="out") as patched:
        _run_tool(audio_denoise, ["-i", files["dir1"], files["c.mp3"]])
    assert _names([c.args[0] for c in patched.call_args_list], tmp_path) == ["dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4", "c.mp3"]


def test_tool_output_with_directory(tmp_path: Path) -> None:
    """-o with a directory resulting in several files exits with code 2"""
    files = _tree(tmp_path)
    with (
        mock.patch.object(sys, "argv", ["videotool", "volume", "-i", files["dir1"], "--volume", "200%", "-o", "out.mp4"]),
        pytest.raises(SystemExit) as e,
    ):
        tools.videotool()
    assert e.value.code == 2


def test_tool_directory_without_matching_file(tmp_path: Path) -> None:
    """A directory without any matching file exits with code 1"""
    files = _tree(tmp_path)
    with mock.patch.object(sys, "argv", ["videotool", "volume", "-i", files["empty"], "--volume", "200%"]), pytest.raises(SystemExit) as e:
        tools.videotool()
    assert e.value.code == 1


def test_tool_continues_after_failure(tmp_path: Path) -> None:
    """A failure on one file doesn't prevent the others from being processed"""
    files = _tree(tmp_path)

    def fail_on_b(filename: str, *args: str) -> str:
        """Fails for the file b.mp4, succeeds for the other files"""
        if filename.endswith("b.mp4"):
            raise ValueError("boom")
        return "out.mp4"

    with (
        mock.patch.object(sys, "argv", ["videotool", "volume", "-i", files["dir1"], "--volume", "200%"]),
        mock.patch("mediatools.videofile.volume", side_effect=fail_on_b) as patched,
        pytest.raises(SystemExit) as e,
    ):
        tools.videotool()
    assert e.value.code == 1
    assert len(patched.call_args_list) == 3


# PDF tools
def test_pdf_split_directory(tmp_path: Path) -> None:
    """pdf-split processes all the PDF files of a directory (recursively)"""
    files = _tree(tmp_path)
    (tmp_path / "dir1" / "f.pdf").write_bytes(b"x")
    with (
        mock.patch.object(sys, "argv", ["pdftool", "split", "-i", files["dir1"], "--ppp", "300"]),
        mock.patch("mediatools.pdf_split.split", return_value=2) as split,
    ):
        tools.pdftool()
    assert _names([c.args[0] for c in split.call_args_list], tmp_path) == ["dir1/f.pdf", "dir1/sub/e.pdf"]


def test_pdf_split_failure(tmp_path: Path) -> None:
    """pdf-split exits with 1 if a file is missing, after having processed the others"""
    files = _tree(tmp_path)
    with (
        mock.patch.object(sys, "argv", ["pdftool", "split", "-i", str(tmp_path / "missing.pdf"), files["dir1/sub/e.pdf"]]),
        mock.patch("mediatools.pdf_split.split", return_value=2) as split,
        pytest.raises(SystemExit) as e,
    ):
        tools.pdftool()
    assert e.value.code == 1
    assert split.call_count == 1


def test_pdf_compress_directory(tmp_path: Path) -> None:
    """pdf-compress processes all the PDF files of a directory"""
    files = _tree(tmp_path)
    with (
        mock.patch.object(sys, "argv", ["pdftool", "compress", "-i", files["dir1"]]),
        mock.patch("mediatools.pdf_compress.compress", side_effect=lambda f, _o, _p: f) as compress,
    ):
        tools.pdftool()
    assert _names([c.args[0] for c in compress.call_args_list], tmp_path) == ["dir1/sub/e.pdf"]


def test_pdf_compress_output_with_several_inputs(tmp_path: Path) -> None:
    """pdf-compress refuses -o with several input files"""
    files = _tree(tmp_path)
    (tmp_path / "dir1" / "f.pdf").write_bytes(b"x")
    with mock.patch.object(sys, "argv", ["pdftool", "compress", "-i", files["dir1"], "-o", "x.pdf"]), pytest.raises(SystemExit) as e:
        tools.pdftool()
    assert e.value.code == 2


def test_pdf_merge_directory(tmp_path: Path) -> None:
    """pdf-merge merges the PDF files of the directories and the PDF files given"""
    files = _tree(tmp_path)
    (tmp_path / "dir1" / "f.pdf").write_bytes(b"x")
    extra = tmp_path / "a.pdf"
    extra.write_bytes(b"x")
    with (
        mock.patch.object(sys, "argv", ["pdftool", "merge", "-i", str(extra), files["dir1"]]),
        mock.patch("mediatools.pdf_merge.merge", return_value="o.pdf") as merge,
    ):
        tools.pdftool()
    assert _names(merge.call_args[0][0], tmp_path) == ["a.pdf", "dir1/f.pdf", "dir1/sub/e.pdf"]


def test_argparse_is_still_standard() -> None:
    """Sanity check of the common arguments: -i takes several values"""
    parser = util.get_common_args("test", "test")
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.parse_args(["-i", "a", "b", "c"]).inputfiles == ["a", "b", "c"]


# Tools whose files used to be given with -f / --files
def test_renamer_inputs(tmp_path: Path) -> None:
    """renamer -i takes files and directories: the image and video files of the directories are renamed"""
    files = _tree(tmp_path)
    with (
        mock.patch.object(sys, "argv", ["renamer", "-i", files["pic.jpg"], files["dir1"], "--video_format", "#SEQ2#", "--photo_format", "#SEQ2#"]),
        mock.patch("mediatools.renamer.get_files_data", return_value={}) as get_data,
        mock.patch("mediatools.renamer.rename_files", return_value=True),
    ):
        renamer.main()
    assert _names(get_data.call_args[0][0], tmp_path) == ["pic.jpg", "dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4"]


def test_renamer_files_alias(tmp_path: Path) -> None:
    """-f and --files are still accepted as aliases of -i"""
    files = _tree(tmp_path)
    for option in ("-f", "--files"):
        with (
            mock.patch.object(sys, "argv", ["renamer", option, files["a.mp4"], "--video_format", "#SEQ2#"]),
            mock.patch("mediatools.renamer.get_files_data", return_value={}) as get_data,
            mock.patch("mediatools.renamer.rename_files", return_value=True),
        ):
            renamer.main()
        assert get_data.call_args[0][0] == [files["a.mp4"]]


def test_datefixer_inputs(tmp_path: Path) -> None:
    """datefixer -i takes files and directories, the image and video files only are processed"""
    files = _tree(tmp_path)
    for option in ("-i", "-f", "--files"):
        with (
            mock.patch.object(sys, "argv", ["datefixer", option, files["pic.jpg"], files["dir1"], "--mode", "filename"]),
            mock.patch("mediatools.datefixer.change_files_date", return_value=0) as change,
        ):
            _main_exit_ok(datefixer)
        assert _names(list(change.call_args[0][2:]), tmp_path) == ["pic.jpg", "dir1/b.mp4", "dir1/sub/d.mp4", "dir1/z.mp4"]


@pytest.mark.parametrize("module", [fix_mp3_meta, audio_normalize], ids=["fix_mp3_meta", "audio_normalize"])
def test_album_tools_input_option(tmp_path: Path, module: ModuleType) -> None:
    """fix-mp3-meta and audio-normalize take -i (and -f as an alias): files and directories, processed album by album"""
    files = _tree(tmp_path)
    for option in ("-i", "-f", "--files"):
        with (
            mock.patch.object(sys, "argv", _argv(module, option, files["dir1"], files["c.mp3"], "--dry-run")),
            mock.patch.object(module, "process_directory") as process_directory,
            mock.patch.object(module, "process_file") as process_file,
            mock.patch.object(module, "mb_lookup_release", return_value=(None, None, None, [], None) if module is audio_normalize else (None, [])),
        ):
            _main_exit_ok(module)
        assert process_file.call_count == 1  # c.mp3 given as a file
        assert process_file.call_args[0][0] == files["c.mp3"]
        # dir1 has no audio file directly in it: only its sub-directory is an album
        assert [Path(c.args[0]).name for c in process_directory.call_args_list] == ["sub"]


def test_file_list_uses_expand_inputs(tmp_path: Path) -> None:
    """fil.file_list expands the directories like the -i option, and filters the files given by type"""
    files = _tree(tmp_path)
    assert _names(fil.file_list(files["dir1"], files["c.mp3"], files["notes.txt"], file_type=fil.FileType.VIDEO_FILE), tmp_path) == [
        "dir1/b.mp4",
        "dir1/sub/d.mp4",
        "dir1/z.mp4",
    ]
