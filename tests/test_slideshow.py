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

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import os
import subprocess
import sys
from unittest.mock import patch
import pytest
import yaml
from mediatools import tools
import mediatools.videofile as video
import mediatools.imagefile as image
import mediatools.media_config as conf
import mediatools.utilities as util
import utilities.file as fil

large_img = None
portrait_img = None

images_full = (
    "it" + os.sep + "img-1770x1291.jpg",
    "it" + os.sep + "img-3000x1682.jpg",
    "it" + os.sep + "img-large.jpg",
    "it" + os.sep + "img-2320x4000.jpg",
    "it" + os.sep + "img-superwide.jpg",
    "it" + os.sep + "img-2880x1924.jpg",
    "it" + os.sep + "img-3000x4000.jpg",
    "it" + os.sep + "img-640x480.jpg",
)

# The slideshow converts each image to a video: the tests use small versions of landscape and portrait images
SMALL_IMAGES = (("img-1770x1291.jpg", 400), ("img-3000x4000.jpg", 300), ("img-640x480.jpg", 320))


@pytest.fixture(scope="module")
def images(tmp_path_factory):
    folder = tmp_path_factory.mktemp("slides")
    return tuple(image.ImageFile("it" + os.sep + name).scale(width, -1, out_file=str(folder / name)) for name, width in SMALL_IMAGES)


@pytest.fixture
def small_default_resolution(monkeypatch):
    """Generate the videos of the slideshows in 320x180 instead of the default (4K) resolution"""
    real_get_property = conf.get_property
    small_res_keys = (conf.VIDEO_RESOLUTION_KEY, conf.SLIDESHOW_RESOLUTION_KEY)
    monkeypatch.setattr(conf, "get_property", lambda name, settings=None: "320x180" if name in small_res_keys else real_get_property(name, settings))


def test_slideshow(images):
    # util.set_debug_level(4)
    vid2_o = video.VideoFile(video.slideshow(*images, resolution="360x200")[0])
    assert vid2_o.duration > 12
    assert vid2_o.resolution.width == 360
    assert vid2_o.resolution.height == 200
    os.remove(vid2_o.filename)


def test_slideshow_without_resolution(images, small_default_resolution):
    # util.set_debug_level(4)
    vid2_o = video.VideoFile(video.slideshow(*images)[0])
    assert vid2_o.duration > 12
    os.remove(vid2_o.filename)


def test_main(images):
    file1, file2 = images[2], images[0]
    out_file = str(images[2]) + ".slideshow-test.mp4"
    with patch.object(sys, "argv", ["videotool", "slideshow", "-g", "4", "-i", file1, file2, "--resolution", "640x360", "-o", out_file]):
        tools.videotool()
    os.remove(out_file)
    os.remove(fil.strip_extension(out_file) + ".yaml")


def test_main_yaml_input(images, tmp_path):
    out_file = str(tmp_path / "from-yaml.mp4")
    yaml_in = tmp_path / "in.yaml"
    photos = [
        {"photo": os.path.abspath(images[0]), "effect": "pan-left", "duration": 3.0, "vertical_drift_pct": 2.5},
        {"photo": os.path.abspath(images[2]), "effect": "zoom-in", "duration": 3.0, "zoom_start_pct": 100.0, "zoom_stop_pct": 120.0},
    ]
    yaml_in.write_text(yaml.safe_dump({"output": out_file, "photos": photos}), encoding="utf-8")
    with patch.object(sys, "argv", ["videotool", "slideshow", "-y", str(yaml_in), "--resolution", "320x180"]):
        tools.videotool()
    assert os.path.isfile(out_file)
    with open(fil.strip_extension(out_file) + ".yaml", encoding="utf-8") as f:
        written = yaml.safe_load(f)["photos"]
    assert [p["effect"] for p in written] == ["pan-left", "zoom-in"]
    assert [p["duration"] for p in written] == [3.0, 3.0]
    assert written[0]["vertical_drift_pct"] == pytest.approx(2.5, abs=0.2)


def test_main_yaml_invalid(tmp_path):
    yaml_in = tmp_path / "bad.yaml"
    yaml_in.write_text("photos: []", encoding="utf-8")
    with patch.object(sys, "argv", ["videotool", "slideshow", "-y", str(yaml_in)]), pytest.raises(SystemExit) as e:
        tools.videotool()
    assert e.value.code == 1


def test_main_requires_inputs():
    with patch.object(sys, "argv", ["videotool", "slideshow"]), pytest.raises(SystemExit) as e:
        tools.videotool()
    assert e.value.code == 2


# Hardware acceleration: the clips of the photos and the slideshow are encoded by the GPU, the filters run on the CPU
@pytest.fixture
def commands():
    """The ffmpeg commands that are run (not executed)"""
    with patch("mediatools.utilities.run_os_cmd") as run:
        yield run


def run_commands(run) -> list[str]:
    return [c.args[0] for c in run.call_args_list]


@pytest.mark.parametrize("effect", ["zoom", "panorama"])
def test_photo_clip_encoded_by_the_gpu(commands, effect):
    getattr(image.ImageFile(images_full[0]), effect)(hw_accel="on")
    (cmd,) = run_commands(commands)
    assert "-c:v h264_nvenc" in cmd
    assert "-hwaccel" not in cmd  # The filters of the effects run on the CPU


@pytest.mark.parametrize("effect", ["zoom", "panorama"])
def test_photo_clip_encoded_by_the_cpu(commands, effect):
    getattr(image.ImageFile(images_full[0]), effect)(hw_accel="off")
    (cmd,) = run_commands(commands)
    assert "nvenc" not in cmd


def test_slideshow_passes_the_mode_to_the_clips(commands):
    with (
        patch.object(video, "__build_slideshow__", return_value="out.mp4", create=True),
        patch.object(image.ImageFile, "to_video", return_value=("clip.mp4", {})) as to_video,
    ):
        video.slideshow(images_full[0], outfile="out.mp4", hw_accel="on")
    assert to_video.call_args.kwargs["hw_accel"] == "on"
    commands.assert_not_called()


@pytest.mark.parametrize(("mode", "nvenc"), [("on", True), ("off", False)])
def test_slideshow_assembly_encoded_by_the_gpu_only(commands, short_video, tmp_path, mode, nvenc):
    video.__build_slideshow__([short_video, short_video], outfile=str(tmp_path / "out.mp4"), resolution="320x180", hw_accel=mode)
    (cmd,) = run_commands(commands)
    assert ("-c:v h264_nvenc" in cmd) is nvenc
    assert "-hwaccel" not in cmd and "cuvid" not in cmd  # Decoding the clips on the GPU and the CPU can't be mixed


def test_slideshow_runs_again_on_the_cpu_when_the_gpu_fails(short_video, tmp_path):
    attempts = []

    def run_os_cmd(cmd, duration=None):
        attempts.append(cmd)
        if "nvenc" in cmd:
            raise subprocess.CalledProcessError(1, cmd)

    with (
        patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd),
        patch.object(image.ImageFile, "to_video", return_value=(short_video, {"photo": "a.jpg"})),
        patch.object(util, "check_hardware_accel", return_value=True),
    ):
        out, _ = video.slideshow(images_full[0], images_full[1], outfile=str(tmp_path / "out.mp4"), resolution="320x180")
    assert out == str(tmp_path / "out.mp4")
    assert "nvenc" in attempts[0]
    assert "nvenc" not in attempts[-1]


# Vertical drift of the panoramas of the photos that are not as wide as 16:9
def test_panorama_logs_the_vertical_drift(commands):
    _, details = image.ImageFile(images_full[0]).panorama(effect=(0, 1, 0.48, 0.52))
    assert details["vertical_drift_pct"] == pytest.approx(4.0)
    _, details = image.ImageFile(images_full[0]).panorama(effect=(0, 1, 0.53, 0.5))
    assert details["vertical_drift_pct"] == pytest.approx(-3.0)
    assert len(run_commands(commands)) == 2


def test_panorama_of_a_wide_photo_has_no_vertical_drift(commands):
    _, details = image.ImageFile(images_full[4]).panorama(effect=(0, 1, 0.45, 0.55))
    assert details["vertical_drift_pct"] == 0.0
    assert len(run_commands(commands)) == 1


def test_to_video_drifts_up_or_down_by_at_most_5_percent(commands):
    drifts = []
    for _ in range(60):
        _, details = image.ImageFile(images_full[0]).to_video(with_effect=True, resolution="320x180")
        if "vertical_drift_pct" in details:
            drifts.append(details["vertical_drift_pct"])
    assert drifts
    assert all(-5.0 <= d <= 5.0 for d in drifts)
    assert any(d > 0 for d in drifts) and any(d < 0 for d in drifts)
    assert commands.call_count == 60
