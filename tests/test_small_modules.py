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

"""Tests of small modules: audio-speed, the Encoder class, the logger, the config files, the filters classes
and the command lines of encode, datefixer and image-to-video. Media commands are mocked."""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import io
import logging
import sys
from datetime import datetime
from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta

from filters import filter as flt
from filters import filters as flts
from cli import encode as cli_encode
from mediatools import audiospeed, config, datefixer, encoder, image2video, log, tools
import mediatools.exceptions as ex
from types import ModuleType
from pathlib import Path


# ---------------------------------------------------------------- audio-speed
@pytest.mark.parametrize(
    ("factor", "expected"),
    [(1.0, ["atempo=1.000000"]), (1.5, ["atempo=1.500000"]), (4.0, ["atempo=2.0", "atempo=2.000000"]), (0.25, ["atempo=0.5", "atempo=0.500000"])],
)
def test_atempo_filters(factor: float, expected: list[str]) -> None:
    """Atempo filters"""
    chain = audiospeed.atempo_filters(factor)
    assert chain == expected
    product = 1.0
    for f in chain:
        product *= float(f.split("=")[1])
    assert product == pytest.approx(factor)


def test_atempo_filters_long_chain() -> None:
    """Atempo filters long chain"""
    assert len(audiospeed.atempo_filters(10.0)) == 4


def test_audio_speed() -> None:
    """Audio speed"""
    audio_file = mock.Mock(abitrate=192000, duration=100.0)
    with mock.patch.object(audiospeed.audio, "AudioFile", return_value=audio_file), mock.patch("mediatools.utilities.run_ffmpeg") as run:
        output = audiospeed.speed("song.mp3", None, 50.0)
    assert output.endswith("song.speed50.mp3")
    cmd, duration = run.call_args.args
    assert '-af "atempo=2.000000"' in cmd
    assert '-b:a "192000"' in cmd
    assert cmd.endswith(f'"{output}"')
    assert duration == pytest.approx(50.0)  # 50% of the duration: twice as fast


def test_audio_speed_without_bitrate_and_output() -> None:
    """Audio speed without bitrate and output"""
    audio_file = mock.Mock(abitrate=None, duration=None)
    with mock.patch.object(audiospeed.audio, "AudioFile", return_value=audio_file), mock.patch("mediatools.utilities.run_ffmpeg") as run:
        assert audiospeed.speed("song.mp3", "out.mp3", 200.0) == "out.mp3"
    cmd, duration = run.call_args.args
    assert "-b:a" not in cmd
    assert '"out.mp3"' in cmd
    assert duration is None


def test_audio_speed_main() -> None:
    """Audio speed main"""
    with (
        mock.patch.object(sys, "argv", ["audiotool", "speed", "-i", "a.mp3", "b.mp3", "--size", "90"]),
        mock.patch.object(audiospeed, "speed", return_value="o.mp3") as speed,
        mock.patch("mediatools.utilities.generated_file"),
    ):
        tools.audiotool()
    assert [(c.args[0], c.args[2]) for c in speed.call_args_list] == [("a.mp3", 90.0), ("b.mp3", 90.0)]


def test_audio_speed_main_invalid_size() -> None:
    """Audio speed main invalid size"""
    with mock.patch.object(sys, "argv", ["audiotool", "speed", "-i", "a.mp3", "--size", "0"]), pytest.raises(SystemExit) as e:
        tools.audiotool()
    assert e.value.code == 1


# ---------------------------------------------------------------- Encoder
def test_encoder_settings() -> None:
    """Encoder settings"""
    enc = encoder.Encoder(vcodec="libx264", vbitrate="1000k", acodec="aac", abitrate="128k", aspect="16:9", start=2, stop=10, format="mp4", unknown=1)
    assert (enc.vcodec, enc.vbitrate, enc.acodec, enc.abitrate, enc.aspect, enc.format) == ("libx264", "1000k", "aac", "128k", "16:9", "mp4")
    assert (enc.start, enc.stop) == (2, 10)


def test_encoder_defaults_and_ignored_settings() -> None:
    """Encoder defaults and ignored settings"""
    enc = encoder.Encoder(vcodec=None)
    assert enc.vcodec == "copy"
    assert enc.acodec == "copy"
    assert enc.start is None
    assert enc.stop is None
    assert not enc.vfilters


def test_encoder_filters() -> None:
    """Encoder filters"""
    enc = encoder.Encoder(start=2, stop=10)
    enc.add_crop_filter(10, 20, 1, 2)
    enc.add_deshake_filter(16, 8)
    enc.add_fade_filter(1)
    assert enc.vfilters[0] == "crop=10:20:1:2"
    assert enc.vfilters[1] == "deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=8"
    assert enc.vfilters[2] == "fade=type=in:duration=1:start_time=2,fade=type=out:duration=1:start_time=9"
    assert enc.get_vfilters_string().count("-filter:v") == 3


def test_encoder_fade_without_start() -> None:
    """Encoder fade without start"""
    enc = encoder.Encoder()
    enc.add_fade_filter(0.5, stop=5)
    assert enc.vfilters[0] == "fade=type=in:duration=0.5:start_time=0,fade=type=out:duration=0.5:start_time=4.5"


def test_encoder_ffmpeg_options() -> None:
    """Encoder ffmpeg options"""
    enc = encoder.Encoder(vcodec="libx264", vbitrate="1000k", format="mp4", start=2, stop=10)
    enc.set_format("mkv")
    enc.add_vfilter("hflip")
    opts = enc.ffmpeg_opts()
    assert opts == '-f mkv -vcodec libx264 -b:v 1000k -acodec copy -ss 2 -to 10 -filter:v "hflip"'


# ---------------------------------------------------------------- log
class _Stream:
    encoding = "ascii"

    def __init__(self) -> None:
        """Creates a stream that records what is written in it"""
        self.written = []
        self.buffer = io.BytesIO()

    def write(self, text: str) -> None:
        """Records the text written"""
        self.written.append(text)

    def flush(self) -> None:
        """Does nothing"""


def _record(message: str = "héllo") -> logging.LogRecord:
    """Returns a log record with a message"""
    return logging.LogRecord("test", logging.INFO, __file__, 1, message, None, None)


def test_log_handler_writes_to_the_stream() -> None:
    """Log handler writes to the stream"""
    stream = io.StringIO()
    handler = log.Utf8StreamHandler(stream)
    handler.emit(_record("hello"))
    assert stream.getvalue() == "hello\n"


def test_log_handler_with_an_unencodable_message_writes_utf8_bytes() -> None:
    """Log handler with an unencodable message writes utf8 bytes"""

    class AsciiStream(_Stream):
        def write(self, text: str) -> None:
            """Accepts only the text that can be encoded in ASCII"""
            text.encode("ascii")

    stream = AsciiStream()
    log.Utf8StreamHandler(stream).emit(_record())
    assert stream.buffer.getvalue() == "héllo\n".encode()


def test_log_handler_with_an_unencodable_message_and_no_buffer() -> None:
    """Log handler with an unencodable message and no buffer"""

    class AsciiStreamNoBuffer:
        encoding = "ascii"

        def __init__(self) -> None:
            """Creates a stream without buffer that records what is written in it"""
            self.written = []

        def write(self, text: str) -> None:
            """Records the text written if it can be encoded in ASCII"""
            text.encode("ascii")
            self.written.append(text)

        def flush(self) -> None:
            """Does nothing"""

    stream = AsciiStreamNoBuffer()
    log.Utf8StreamHandler(stream).emit(_record())
    assert stream.written == ["h?llo\n"]


def test_log_handler_error_while_formatting() -> None:
    """Log handler error while formatting"""
    handler = log.Utf8StreamHandler(io.StringIO())
    with mock.patch.object(handler, "format", side_effect=ValueError("bad record")), mock.patch.object(handler, "handleError") as handle:
        handler.emit(_record())
    handle.assert_called_once()


def test_log_handler_recursion_error_is_raised() -> None:
    """Log handler recursion error is raised"""
    handler = log.Utf8StreamHandler(io.StringIO())
    with mock.patch.object(handler, "format", side_effect=RecursionError), pytest.raises(RecursionError):
        handler.emit(_record())


def test_log_handler_error_while_writing_the_bytes() -> None:
    """Log handler error while writing the bytes"""

    class BrokenStream:
        encoding = "ascii"

        def write(self, text: str) -> None:
            """Accepts only the text that can be encoded in ASCII"""
            text.encode("ascii")

        def flush(self) -> None:
            """Does nothing"""

        @property
        def buffer(self) -> None:
            """Fails: the buffer of the stream is closed"""
            raise OSError("closed")

    handler = log.Utf8StreamHandler(BrokenStream())
    with mock.patch.object(handler, "handleError") as handle:
        handler.emit(_record())
    handle.assert_called_once()


def test_set_logger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set logger"""
    previous = log.logger
    monkeypatch.chdir(tmp_path)
    try:
        log.set_logger("unit-test-logger")
        assert log.logger.name == "unit-test-logger"
        assert not log.logger.propagate
        assert len(log.logger.handlers) == 2
        log.logger.info("a message")
        for handler in list(log.logger.handlers):
            handler.close()
        assert (tmp_path / "unit-test-logger.log").exists()
    finally:
        logging.getLogger("unit-test-logger").handlers.clear()
        log.logger = previous


@pytest.mark.parametrize(
    ("level", "expected"),
    [(5, logging.DEBUG), (4, logging.DEBUG), (3, logging.INFO), (2, logging.WARNING), (1, logging.ERROR), (0, logging.CRITICAL)],
)
def test_get_logging_level(level: int, expected: int) -> None:
    """Get logging level"""
    assert log.get_logging_level(level) == expected


# ---------------------------------------------------------------- config
def test_load_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Load config"""
    home = tmp_path / "home"
    home.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    (home / ".unit-conf.properties").write_text("a=home\nb=on\nc=12\nd=1.5\ne=no\nf=text\ng=true\n")
    (work / "unit-conf.properties").write_text("a=local\n")
    monkeypatch.setattr("os.path.expanduser", lambda _p: str(home))
    monkeypatch.chdir(work)
    monkeypatch.setattr(config, "_CONFIG_SETTINGS", None)
    settings = config.load("unit-conf", {"extra": "yes"})
    assert settings["a"] == "local"  # The local file overrides the file of the home directory
    assert settings["b"] is True
    assert settings["c"] == 12
    assert settings["d"] == 1.5
    assert settings["e"] is False
    assert settings["f"] == "text"
    assert settings["g"] is True
    assert settings["extra"] is True


def test_load_config_without_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Load config without files"""
    monkeypatch.setattr("os.path.expanduser", lambda _p: str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_CONFIG_SETTINGS", None)
    assert config.load("does-not-exist") == {}


def test_load_config_without_permission(tmp_path: Path) -> None:
    """Load config without permission"""
    with mock.patch("builtins.open", side_effect=PermissionError):
        assert not config.load_properties_file(tmp_path / "x.properties")


# ---------------------------------------------------------------- filters (filters/filter.py)
def test_simple_filter() -> None:
    """Simple filter"""
    f = flt.Simple(flt.VIDEO_TYPE, stream_in="0:v", stream_out="out", filters=["a", "b"])
    assert str(f) == '-vf "[0:v]a,b[out]"'
    f.append("c")
    f.insert(0, "z")
    f.extend(["d"])
    assert str(f) == '-vf "[0:v]z,a,b,c,d[out]"'
    assert str(flt.Simple(flt.AUDIO_TYPE, filters="volume=2")) == '-af "volume=2"'
    assert str(flt.Simple()) == ""


def test_complex_filter() -> None:
    """Complex filter"""
    video_a, video_b = mock.Mock(filename="a.mp4"), mock.Mock(filename="b.mp4")
    c = flt.Complex(video_a, video_b)
    first = c.add_filtergraph(0, "scale=10:20")
    second = c.add_filtergraph([first, 1], flt.Overlay(5, 6))
    assert (first, second) == ("out0", "out1")
    assert str(c) == '-filter_complex "[0]scale=10:20[out0];[out0][1]overlay=5:6[out1]"'
    assert c.format_inputs() == '-i "a.mp4" -i "b.mp4"'
    c.insert_input(0, mock.Mock(filename="c.mp4"))
    assert c.format_inputs().startswith('-i "c.mp4"')


@pytest.mark.parametrize(
    ("flt_obj", "expected"),
    [
        (flt.Fade(2.0, "in", 1.0), "fade=t=in:st=2.0:d=1.0:alpha=1"),
        (flt.Fade(direction="OUT", alpha=0), "fade=t=out:st=0.0:d=0.5:alpha=0"),
        (flt.FadeIn(duration=2), "fade=t=in:st=0.0:d=2:alpha=1"),
        (flt.FadeOut(start=8.5, duration=1.5), "fade=t=out:st=8.5:d=1.5:alpha=1"),
        (flt.Sar("16:9"), "setsar=16/9"),
        (flt.Trim(5), "trim=start=0:end=5"),
        (flt.Trim(5, 1, duration=2), "trim=start=1:end=5:duration=2"),
        (flt.Scale(640, 360), "'scale=640:360'"),
        (flt.Scale(640, 360, flags="lanczos"), "'scale=640:360',flags=lanczos"),
        (flt.ScaleCuda(640, 360, format="nv12"), "'scale=640:360':format=nv12"),
        (flt.Crop(100, 50), "crop=100:50:x:y"),
        (flt.crop(100, 50, 3, 4), "crop=100:50:3:4"),
        (flt.Reverse(), "reverse"),
        (flt.Areverse(), "areverse"),
        (flt.Volume("2"), "volume=2"),
        (flt.Volume("-6dB", precision="fixed"), "volume=-6dB:precision=fixed"),
        (flt.Overlay(), "overlay=0:0"),
        (flt.OverlayCuda("1", "2"), "overlay_cuda=1:2"),
        (flt.Deshake(), "deshake=x=-1:y=-1:w=-1:h=-1:rx=32:ry=32"),
        (flt.deshake(16, 8, edge="mirror"), "deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=8:edge=mirror"),
        (flt.Rotate("PI/2"), "rotate=PI/2"),
        (flt.Rotate("PI/2", fillcolor="black"), "rotate=PI/2:fillcolor=black"),
        (flt.Transpose(), "transpose=1"),
        (flt.Transpose(-90), "transpose=2"),
        (flt.Transpose(5), "transpose=5"),
        (flt.Transpose("clock"), "transpose=clock"),
    ],
)
def test_filter_classes(flt_obj: object, expected: str) -> None:
    """Filter classes"""
    assert str(flt_obj) == expected


@pytest.mark.parametrize("transposition", ["sideways", 9, -3])
def test_invalid_transpose(transposition: int | str) -> None:
    """Invalid transpose"""
    with pytest.raises(ex.InputError):
        flt.Transpose(transposition)


def test_filter_functions() -> None:
    """Filter functions"""
    assert flt.setpts("PTS-STARTPTS") == "setpts=PTS-STARTPTS"
    assert flt.select("gt(n,3)") == "select='gt(n,3)'"
    assert flt.fade_in(1, 2) == "fade=t=in:st=1:d=2:alpha=1"
    assert flt.fade_out(1, 2, 0) == "fade=t=out:st=1:d=2:alpha=0"
    assert flt.speed(2) == "select='not(mod(n,2.0))',setpts=N/FRAME_RATE/TB"
    assert flt.speed("50%") == "setpts=2.0*PTS"
    assert flt.zoompan("x", "y", "z", d=100, fps=25) == "zoompan=z='z':x='x':y='y':d=100:fps=25"
    assert flt.format(["yuv420p", "yuva420p"]) == "format=pix_fmts=yuv420p|yuva420p"
    assert flt.format("yuv420p") == "format=pix_fmts=yuv420p"
    assert flt.filtercomplex(["a", "b"]) == '-filter_complex " a;  b"'
    assert flt.filtercomplex(None) == ""
    assert flt.vfilter(["a", "b"]) == '-vf "a,b"'
    assert flt.vfilter([]) == ""
    assert flt.afilter(["a", "b"]) == '-af "a,b"'
    assert flt.afilter(None) == ""
    assert flt.inputs_str(["a.mp4", "b.mp4"]) == '-i "a.mp4" -i "b.mp4"'
    assert flt.format_options(["-a", "-b"]) == "-a -b"
    assert flt.format_options(None) == ""
    assert flt.metadata("title", "x") == '-metadata title="x"'
    assert flt.metadata("title", "x", 1) == '-metadata:s:a:1 title="x"'
    assert flt.metadata("title", "x", 0, "s:v") == '-metadata:s:v:0 title="x"'
    assert flt.vcodec("libx264") == "-vcodec libx264"
    assert flt.acodec("aac") == "-acodec aac"
    assert flt.disposition(1, 3) == "-disposition:a:0 none -disposition:a:1 default -disposition:a:2 none"
    assert flt.hw_accel_input(hw_accel=True) == "-hwaccel cuvid -c:v h264_cuvid"
    assert flt.hw_accel_input() == ""
    assert flt.hw_accel_output(hw_accel=True) == "-c:v h264_nvenc"
    assert flt.hw_accel_output(hw_accel=False) == ""


def test_filter_streams() -> None:
    """Filter streams"""
    assert flt.in_out("scale=1:2", ["a", "b"], "c") == "[a][b]scale=1:2[c]"
    assert flt.wrap_in_streams(["x", "y"], "in", "out") == "[in]x,y[out]"
    assert flt.wrap_in_streams("x", "in", "out") == "[in]x[out]"
    with pytest.raises(flt.FilterError):
        flt.in_out("x", 5, "c")
    with pytest.raises(flt.FilterError):
        flt.wrap_in_streams(5, "in", "out")
    with pytest.raises(flt.FilterError):
        flt.format(5)


def test_filter_error_message() -> None:
    """Filter error message"""
    assert flt.FilterError("oops").message == "oops"


# filters/filters.py
def test_filters_module() -> None:
    """Filters module"""
    assert flts.zoompan("x", "y", "z", d=1) == "zoompan=z='z':x='x':y='y':d=1"
    assert flts.trim(duration=2) == "trim=duration=2"
    assert flts.trim(start=1, stop=2) == "trim=start=1stop=2"
    with pytest.raises(flts.FilterError):
        flts.trim()
    assert flts.overlay(1, 2) == "overlay=1:2"
    assert flts.rotate(90) == "transpose=1"
    assert flts.rotate(-90) == "transpose=2"
    with pytest.raises(ex.InputError):
        flts.rotate("sideways")
    with pytest.raises(ex.InputError):
        flts.rotate(9)


# ---------------------------------------------------------------- datefixer
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("IMG_2017-05-07 08.13.42.jpg", datetime(2017, 5, 7, 8, 13, 42)),
        ("20170507_123422.mp4", datetime(2017, 5, 7, 12, 34, 22)),
        ("2017-05-07 08h13m42s.mp4", datetime(2017, 5, 7, 8, 13, 42)),
        ("holidays 2017-05-07.jpg", datetime(2017, 5, 7)),
    ],
)
def test_guess_date(text: str, expected: datetime) -> None:
    """Guess date"""
    assert datefixer.guess_date(text) == expected


def test_guess_date_not_found() -> None:
    """Guess date not found"""
    assert datefixer.guess_date("no date here") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+0001-02-03 04:05:06", relativedelta(years=1, months=2, days=3, hours=4, minutes=5, seconds=6)),
        ("-0001-02-03", relativedelta(years=-1, months=-2, days=-3)),
        ("+01:02:03", relativedelta(hours=1, minutes=2, seconds=3)),
        ("-00:30:00", relativedelta(minutes=-30)),
    ],
)
def test_guess_offset(text: str, expected: relativedelta) -> None:
    """Guess offset"""
    assert datefixer.guess_offset(text) == expected


def test_guess_offset_invalid() -> None:
    """Guess offset invalid"""
    assert datefixer.guess_offset("+abc") is None


@pytest.fixture
def exif(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Replaces the functions of the videos that read and write the EXIF data (the creation date is 2020-01-01 12:00:00). Returns the module of the
    videos"""
    monkeypatch.setattr(datefixer.videofile, "get_exif", mock.Mock())
    monkeypatch.setattr(datefixer.videofile, "set_creation_date", mock.Mock(return_value=True))
    monkeypatch.setattr(datefixer.videofile, "get_creation_date", mock.Mock(return_value=datetime(2020, 1, 1, 12, 0, 0)))
    return datefixer.videofile


def test_change_file_date_from_the_file_name(exif: ModuleType) -> None:
    """Change file date from the file name"""
    assert datefixer.change_file_date("dir/20170507_123422.mp4", "filename") == ("dir/20170507_123422.mp4", True)
    exif.set_creation_date.assert_called_once_with("dir/20170507_123422.mp4", datetime(2017, 5, 7, 12, 34, 22))


def test_change_file_date_without_date_in_the_name(exif: ModuleType) -> None:
    """Change file date without date in the name"""
    assert datefixer.change_file_date("dir/clip.mp4", "filename")[1] is False
    exif.set_creation_date.assert_not_called()


def test_change_file_date_with_an_offset(exif: ModuleType) -> None:
    """Change file date with an offset"""
    assert datefixer.change_file_date("clip.mp4", "offset", "+01:00:00")[1] is True
    exif.set_creation_date.assert_called_once_with("clip.mp4", datetime(2020, 1, 1, 13, 0, 0))


def test_change_file_date_with_an_invalid_offset(exif: ModuleType) -> None:
    """Change file date with an invalid offset"""
    assert datefixer.change_file_date("clip.mp4", "offset", "+nonsense")[1] is False


def test_change_file_date_absolute(exif: ModuleType) -> None:
    """Change file date absolute"""
    assert datefixer.change_file_date("clip.mp4", "absolute", "2018-02-03 04:05:06")[1] is True
    exif.set_creation_date.assert_called_once_with("clip.mp4", datetime(2018, 2, 3, 4, 5, 6))


def test_change_file_date_unknown_mode(exif: ModuleType) -> None:
    """Change file date unknown mode"""
    assert datefixer.change_file_date("clip.mp4", "weird")[1] is False


def test_change_files_date(exif: ModuleType) -> None:
    """Change files date"""
    assert datefixer.change_files_date("filename", "", "20170507_123422.mp4", "no-date.mp4") == 1


def test_change_files_date_task_failure(exif: ModuleType) -> None:
    """Change files date task failure"""
    with mock.patch.object(datefixer, "change_file_date", side_effect=ValueError("boom")):
        assert datefixer.change_files_date("filename", "", "a.mp4") == 0


def run_datefixer(*args: object) -> int | str | None:
    """Runs the datefixer with the arguments given and returns its exit code"""
    with mock.patch.object(sys, "argv", ["datefixer", *args]), pytest.raises(SystemExit) as e:
        datefixer.main()
    return e.value.code


def test_datefixer_main_filename_mode() -> None:
    """Datefixer main filename mode"""
    with mock.patch.object(datefixer, "change_files_date") as change:
        assert run_datefixer("-i", "a.mp4", "b.jpg", "c.txt", "--mode", "filename") == 0
    assert change.call_args.args == ("filename", "", "a.mp4", "b.jpg")  # The text file is not an image or a video


@pytest.mark.parametrize("mode", ["offset", "absolute"])
def test_datefixer_main_offset_and_absolute_modes(mode: str) -> None:
    """Datefixer main offset and absolute modes"""
    with mock.patch.object(datefixer, "change_files_date") as change:
        assert run_datefixer("-i", "a.mp4", "--mode", mode, "--offset", "+01:00:00") == 0
    assert change.call_args.args == (mode, "+01:00:00", "a.mp4")


@pytest.mark.parametrize("mode", ["offset", "absolute"])
def test_datefixer_main_offset_is_required(mode: str) -> None:
    """Datefixer main offset is required"""
    assert run_datefixer("-i", "a.mp4", "--mode", mode) == 1


def test_datefixer_main_year_mode(exif: ModuleType) -> None:
    """Datefixer main year mode"""
    dates = {"good.mp4": datetime(2020, 1, 1), "bad.mp4": datetime(1999, 1, 1)}
    exif.get_creation_date.side_effect = lambda f: dates[f]
    assert run_datefixer("-i", "good.mp4", "bad.mp4", "--mode", "year", "--year", "2020") == 0
    exif.set_creation_date.assert_called_once_with("bad.mp4", datetime(2020, 1, 1))


def test_datefixer_main_year_mode_needs_two_files(exif: ModuleType) -> None:
    """Datefixer main year mode needs two files"""
    assert run_datefixer("-i", "a.mp4", "--mode", "year", "--year", "2020") == 1


def test_datefixer_main_year_mode_without_a_bad_file(exif: ModuleType) -> None:
    """Datefixer main year mode without a bad file"""
    exif.get_creation_date.side_effect = lambda _f: datetime(2020, 1, 1)
    assert run_datefixer("-i", "a.mp4", "b.mp4", "--mode", "year", "--year", "2020") == 1
    exif.set_creation_date.assert_not_called()


def test_datefixer_main_without_year_or_offset() -> None:
    """Datefixer main without year or offset"""
    assert run_datefixer("-i", "a.mp4", "--mode", "year") == 1


# ---------------------------------------------------------------- encode (cli)
def test_cli_build_file_name(tmp_path: Path) -> None:
    """Cli build file name"""
    src = str(tmp_path / "clip.v1.mp4")
    assert cli_encode.build_file_name(src, "640px") == str(tmp_path / "clip.v1.640px.mp4")
    (tmp_path / "clip.v1.640px.mp4").write_text("x")
    (tmp_path / "clip.v1.640px.1.mp4").write_text("x")
    assert cli_encode.build_file_name(src, "640px") == str(tmp_path / "clip.v1.640px.2.mp4")
    assert cli_encode.build_file_name(src, "x", "mkv") == str(tmp_path / "clip.v1.x.mkv")


def run_cli_encode(*args: object) -> tuple[mock.MagicMock, mock.MagicMock, mock.MagicMock]:
    """Runs the encode command with the arguments given, replacing the video functions. Returns the mocks of the video, of the creation date and of
    the renaming"""
    with (
        mock.patch.object(sys, "argv", ["videotool", "encode", *args]),
        mock.patch.object(cli_encode.vf, "VideoFile") as video_file,
        mock.patch.object(cli_encode.vf, "set_creation_date") as set_date,
        mock.patch.object(cli_encode.vf, "get_creation_date", return_value="THE-DATE"),
        mock.patch.object(cli_encode.fil, "rename") as rename,
        pytest.raises(SystemExit) as e,
    ):
        tools.videotool()
    assert e.value.code == 0
    return video_file, set_date, rename


def test_cli_encode_name_of_the_output(tmp_path: Path) -> None:
    """Cli encode name of the output"""
    video, set_date, rename = run_cli_encode(
        "-i", str(tmp_path / "a.mp4"), "--width", "1920", "--vbitrate", "6000k", "--vcodec", "x265", "--fps", "50"
    )
    assert video.call_args.args == (str(tmp_path / "a.mp4"),)
    assert video.return_value.encode.call_args.kwargs["target_file"] == str(tmp_path / "a.1920px.6000k.x265.50fps.mp4")
    set_date.assert_called_once_with(str(tmp_path / "a.1920px.6000k.x265.50fps.mp4"), "THE-DATE")
    rename.assert_not_called()


def test_cli_encode_default_name_and_media_files_only(tmp_path: Path) -> None:
    """Cli encode default name and media files only"""
    video, _, _ = run_cli_encode("-i", str(tmp_path / "a.mp4"), str(tmp_path / "notes.txt"))
    assert video.call_count == 1
    assert video.return_value.encode.call_args.kwargs["target_file"] == str(tmp_path / "a.encoded.mp4")


def test_cli_encode_keep_name(tmp_path: Path) -> None:
    """Cli encode keep name"""
    src = str(tmp_path / "a.mp4")
    _, _, rename = run_cli_encode("-i", src, "--keepName")
    out = str(tmp_path / "a.encoded.mp4")
    assert [c.args for c in rename.call_args_list] == [(src, str(tmp_path / "a.original.mp4"), False), (out, src)]


# ---------------------------------------------------------------- image-to-video
def run_image2video(*args: object) -> int | str | None:
    """Runs the image to video command with the arguments given and returns its exit code"""
    with (
        mock.patch.object(sys, "argv", ["imagetool", "to-video", *args]),
        mock.patch("mediatools.utilities.generated_file"),
        pytest.raises(SystemExit) as e,
    ):
        tools.imagetool()
    return e.value.code


def test_image2video_zoom() -> None:
    """Image2video zoom"""
    with mock.patch.object(image2video.image, "ImageFile") as image_file:
        image_file.return_value.zoom.return_value = "zoom.mp4"
        assert run_image2video("-i", "a.jpg", "--style", "zoom", "--bounds", "1,1.5", "--duration", "3", "--resolution", "640x360") == 0
    image_file.assert_called_once_with("a.jpg")
    kwargs = image_file.return_value.zoom.call_args.kwargs
    assert kwargs["resolution"] == "640x360"
    assert kwargs["effect"] == [1.0, 1.5]
    assert kwargs["duration"] == 3.0
    image_file.return_value.panorama.assert_not_called()


def test_image2video_panorama() -> None:
    """Image2video panorama"""
    with mock.patch.object(image2video.image, "ImageFile") as image_file:
        image_file.return_value.panorama.return_value = "pan.mp4"
        assert run_image2video("-i", "a.jpg", "b.jpg", "--style", "panorama") == 0
    assert image_file.return_value.panorama.call_count == 2
    assert "resolution" in image_file.return_value.panorama.call_args.kwargs
    assert "effect" not in image_file.return_value.panorama.call_args.kwargs


def test_image2video_input_error() -> None:
    """Image2video input error"""
    with mock.patch.object(image2video.image, "ImageFile") as image_file:
        image_file.return_value.zoom.side_effect = ex.InputError("bad zoom", "image2video")
        assert run_image2video("-i", "a.jpg", "--style", "zoom") != 0
