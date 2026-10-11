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

"""Tests of the audio-denoise tool"""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import audio_denoise as dn

VIDEO = "it" + os.sep + "video-720p.mp4"
AUDIO = "it" + os.sep + "seal.mp3"


@pytest.mark.parametrize(
    ("level", "cutoff", "reduction"),
    [("light", 80, 6), ("medium", 120, 12), ("strong", 200, 20)],
)
def test_wind_levels(level: str, cutoff: int, reduction: int) -> None:
    """The wind method is a high-pass filter followed by an adaptive FFT denoiser, parameters come from the level"""
    assert dn.build_filter("wind", level=level) == f"highpass=f={cutoff}:poles=2,afftdn=nr={reduction}:nf=-50:tn=1"


def test_wind_is_default() -> None:
    """Wind noise reduction is the default method, at medium level"""
    assert dn.build_filter() == dn.build_filter("wind", level="medium")


def test_wind_overrides() -> None:
    """--cutoff, --reduction and --noise-floor override the level"""
    assert dn.build_filter("wind", level="light", cutoff=150, reduction=18.5, noise_floor=-40) == "highpass=f=150:poles=2,afftdn=nr=18.5:nf=-40:tn=1"


def test_afftdn() -> None:
    """The afftdn method has no high-pass and defaults to 12 dB"""
    assert dn.build_filter("afftdn") == "afftdn=nr=12:nf=-50"
    assert dn.build_filter("afftdn", reduction=20, noise_floor=-30) == "afftdn=nr=20:nf=-30"


def test_arnndn(tmp_path: Path) -> None:
    """The arnndn method needs an existing model file"""
    model = tmp_path / "std.rnnn"
    model.write_text("x")
    flt = dn.build_filter("arnndn", model=str(model), mix=0.5)
    assert flt.startswith("arnndn=m='") and flt.endswith("':mix=0.5")
    assert "\\" not in flt.replace(r"\:", "")


@pytest.mark.parametrize(
    "options",
    [
        {"method": "wind", "level": "huge"},
        {"method": "wind", "reduction": 0},
        {"method": "wind", "reduction": 100},
        {"method": "wind", "noise_floor": -10},
        {"method": "wind", "cutoff": 5},
        {"method": "wind", "cutoff": 5000},
        {"method": "arnndn"},
        {"method": "arnndn", "model": "nope.rnnn"},
        {"method": "foo"},
    ],
)
def test_invalid_options(options: dict) -> None:
    """Invalid parameters are rejected"""
    with pytest.raises(ValueError):  # noqa: PT011
        dn.build_filter(**options)


def test_invalid_mix(tmp_path: Path) -> None:
    """The mix is limited to -1..1"""
    model = tmp_path / "std.rnnn"
    model.write_text("x")
    with pytest.raises(ValueError, match="--mix"):
        dn.build_filter("arnndn", model=str(model), mix=2)


def test_denoise_video_command() -> None:
    """For a video the video stream is copied and only the audio is filtered"""
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        out = dn.denoise(VIDEO, level="strong")
    cmd = run.call_args[0][0]
    assert out.endswith(".denoised.mp4")
    assert '-af "highpass=f=200:poles=2,afftdn=nr=20:nf=-50:tn=1"' in cmd
    assert "-c:v copy" in cmd
    assert cmd.endswith(f'"{out}"')


def test_denoise_audio_command() -> None:
    """For an audio file there is no video codec option"""
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        out = dn.denoise(AUDIO, method="afftdn")
    cmd = run.call_args[0][0]
    assert out.endswith(".denoised.mp3")
    assert "-c:v" not in cmd
    assert '-af "afftdn=nr=12:nf=-50"' in cmd


def test_denoise_explicit_output() -> None:
    """The output file name can be given"""
    with mock.patch("mediatools.utilities.run_ffmpeg"):
        assert dn.denoise(VIDEO, "out.mp4") == "out.mp4"


def test_denoise_not_a_media_file() -> None:
    """An image is rejected"""
    with pytest.raises(ValueError, match="not an audio or video file"):
        dn.denoise("it" + os.sep + "img-1770x1291.jpg")


def test_main() -> None:
    """main() denoises each input file with the options given"""
    argv = ["audio-denoise", "-i", VIDEO, AUDIO, "--level", "light", "--cutoff", "100"]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch("mediatools.audio_denoise.denoise", return_value="o.mp4") as denoise,
        pytest.raises(SystemExit) as e,
    ):
        dn.main()
    assert e.value.code == 0
    assert denoise.call_count == 2  # noqa: PLR2004
    assert denoise.call_args.kwargs["level"] == "light"
    assert denoise.call_args.kwargs["cutoff"] == 100  # noqa: PLR2004


def test_main_invalid_option() -> None:
    """An invalid option exits with code 2 before any processing"""
    with mock.patch.object(sys, "argv", ["audio-denoise", "-i", VIDEO, "--method", "arnndn"]), pytest.raises(SystemExit) as e:
        dn.main()
    assert e.value.code == 2  # noqa: PLR2004


def test_main_output_with_several_inputs() -> None:
    """-o is refused with several input files"""
    with mock.patch.object(sys, "argv", ["audio-denoise", "-i", VIDEO, AUDIO, "-o", "x.mp4"]), pytest.raises(SystemExit) as e:
        dn.main()
    assert e.value.code == 2  # noqa: PLR2004


def test_main_failure() -> None:
    """A failing file makes the command exit with 1"""
    with (
        mock.patch.object(sys, "argv", ["audio-denoise", "-i", VIDEO]),
        mock.patch("mediatools.audio_denoise.denoise", side_effect=RuntimeError("boom")),
        pytest.raises(SystemExit) as e,
    ):
        dn.main()
    assert e.value.code == 1
