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

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import mediatools.exceptions as ex
import mediatools.imagefile as img
import mediatools.utilities as util
import utilities.file as fil
from mediatools import poster, tools

DIR = "it" + os.sep
IMG1 = DIR + "img-640x480.jpg"
IMG2 = DIR + "img-1770x1291.jpg"
IMG3 = DIR + "img-3000x4000.jpg"
IMG4 = DIR + "img-3000x1682.jpg"
IMG5 = DIR + "img-2880x1924.jpg"
IMG6 = DIR + "img-4000x3000.jpg"
TMP1 = util.get_tmp_file() + ".jpg"


def _remove_with_yaml(out_file: str) -> None:
    """Removes a generated poster and the YAML file written next to it"""
    os.remove(out_file)
    yaml_file = fil.strip_extension(out_file) + ".yaml"
    if os.path.isfile(yaml_file):
        os.remove(yaml_file)


def test_main() -> None:
    """Main"""
    with patch.object(sys, "argv", ["imagetool", "poster", "-g", "4", "-b", "black", "--gutter", "10", "-i", IMG1, IMG2, IMG3, IMG4, IMG5, IMG6]):
        try:
            assert tools.imagetool() is None
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_help() -> None:
    """Main help"""
    with patch.object(sys, "argv", ["imagetool", "poster", "-i", IMG1, IMG2, "-h"]):
        with pytest.raises(SystemExit) as e:
            tools.imagetool()
        assert int(str(e.value)) == 0


def test_main_stretch_option_was_removed() -> None:
    """--stretch was removed: images are now always rescaled to their column's width (#poster-columns)"""
    with patch.object(sys, "argv", ["imagetool", "poster", "--stretch", "-i", IMG1, IMG2]):
        with pytest.raises(SystemExit) as e:
            tools.imagetool()
        assert int(str(e.value)) == 2


def test_main_bad_option() -> None:
    """Main bad option"""
    with patch.object(sys, "argv", ["imagetool", "poster", "-b", "-i", IMG1, IMG2, "--badoption", "yes"]):
        with pytest.raises(SystemExit) as e:
            tools.imagetool()
        assert int(str(e.value)) == 2


def test_main_no_file() -> None:
    """Main no file"""
    with patch.object(sys, "argv", ["imagetool", "poster", "-g", "4", "-b", "black", "--gutter", "10"]):
        with pytest.raises(SystemExit) as e:
            tools.imagetool()
        assert int(str(e.value)) == 2


def test_main_other_options() -> None:
    """Main other options"""
    with patch.object(sys, "argv", ["imagetool", "poster", "-b", "white", "--gutter", "50", "--layout", "1x2", "-i", IMG1, IMG2]):
        try:
            assert tools.imagetool() is None
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_with_output() -> None:
    """Main with output"""
    with patch.object(sys, "argv", ["imagetool", "poster", "-i", IMG1, IMG2, "-o", TMP1, "-g", "4"]):
        try:
            tools.imagetool()
            assert img.ImageFile(TMP1).width > 0
        except SystemExit as e:
            assert int(str(e)) == 0
            assert img.ImageFile(TMP1).width > 0
    _remove_with_yaml(TMP1)


def test_main_with_output2() -> None:
    """Main with output2: orientation and aspect_ratio drive the automatic number of columns"""
    with patch.object(
        sys, "argv", ["imagetool", "poster", "-i", IMG1, IMG2, "-b", "white", "--gutter", "50", "--orientation", "landscape", "-o", TMP1, "-g", "4"]
    ):
        try:
            tools.imagetool()
            assert img.ImageFile(TMP1).width > 0
        except SystemExit as e:
            assert int(str(e)) == 0
            assert img.ImageFile(TMP1).width > 0
    _remove_with_yaml(TMP1)


# ------------------------------------------------------------------------------
# Column layout (auto layout, round-robin distribution, rendering)
# ------------------------------------------------------------------------------


def test_auto_poster_columns_default_equal_widths() -> None:
    """By default each column gets an equal share of the width, and the images are distributed round-robin"""
    columns = img.auto_poster_columns(IMG1, IMG2, IMG3, IMG4, layout="1x2")
    assert [c["width"] for c in columns] == ["50%", "50%"]
    assert [os.path.basename(f) for f in columns[0]["images"]] == [os.path.basename(IMG1), os.path.basename(IMG3)]
    assert [os.path.basename(f) for f in columns[1]["images"]] == [os.path.basename(IMG2), os.path.basename(IMG4)]


def test_auto_poster_columns_width_for_three_and_four_columns() -> None:
    """The default width of 3 columns is 33.33% each, of 4 columns 25% each"""
    columns3 = img.auto_poster_columns(IMG1, IMG2, IMG3, layout="1x3")
    assert [c["width"] for c in columns3] == ["33.33%", "33.33%", "33.33%"]
    columns4 = img.auto_poster_columns(IMG1, IMG2, IMG3, IMG4, layout="1x4")
    assert [c["width"] for c in columns4] == ["25%", "25%", "25%", "25%"]


def test_auto_layout_picks_columns_to_approximate_orientation() -> None:
    """Without a layout, the number of columns is picked to approximate the target orientation (default aspect ratio 70/50, the most
    common poster printing format)"""
    files = [img.ImageFile(IMG1)] * 4  # 4 landscape (4:3) images
    assert img.__auto_layout__(files, orientation="portrait") == (4, 1)
    assert img.__auto_layout__(files, orientation="landscape") == (2, 2)


def test_auto_layout_uses_aspect_ratio_string() -> None:
    """A "W:H" or "W/H" aspect ratio string is used as the target ratio"""
    files = [img.ImageFile(IMG1)] * 4
    assert img.__auto_layout__(files, aspect_ratio="1:4") == (4, 1)
    assert img.__auto_layout__(files, aspect_ratio="1/4") == (4, 1)


def test_auto_layout_defaults_to_poster_aspect_ratio() -> None:
    """Without orientation, aspect_ratio nor layout, the poster defaults to whichever of the 2 standard printing formats
    (70/50 landscape or 50/70 portrait) best fits the images"""
    landscape_files = [img.ImageFile(IMG1)] * 6  # 640x480, ratio 1.333 (> 1)
    assert img.__auto_layout__(landscape_files) == (3, 2)
    portrait_files = [img.ImageFile(DIR + "img-2320x4000.jpg")] * 6  # Genuinely portrait pixels (2320x4000, ratio 0.58 < 1)
    assert img.__auto_layout__(portrait_files) == (2, 3)


def test_parse_gutter() -> None:
    """A gutter is a number of pixels (plain or "NNpx"), or a percentage of a reference value"""
    assert img.__parse_gutter__("64px", 1000) == 64
    assert img.__parse_gutter__("5%", 1000) == 50
    assert img.__parse_gutter__(20, 1000) == 20
    assert img.__parse_gutter__("20", 1000) == 20


def test_parse_percent() -> None:
    """A percentage is a number, or a string with a trailing %"""
    assert img.__parse_percent__("33.33%") == 33.33
    assert img.__parse_percent__(50) == 50.0


def test_parse_aspect_ratio() -> None:
    """An aspect ratio is a number, or a "W:H" or "W/H" string"""
    assert img.__parse_aspect_ratio__("4:3") == pytest.approx(4 / 3)
    assert img.__parse_aspect_ratio__("4/3") == pytest.approx(4 / 3)
    assert img.__parse_aspect_ratio__(1.3333) == pytest.approx(1.3333)


def test_append_to_columns_round_robin_from_shortest() -> None:
    """Appended photos go round-robin into the columns, starting with the shortest one"""
    columns = [{"width": "50%", "images": ["a.jpg", "b.jpg"]}, {"width": "50%", "images": ["c.jpg"]}]
    result = img.append_to_columns(columns, IMG1, IMG2)
    assert [os.path.basename(f) for f in result[0]["images"]] == ["a.jpg", "b.jpg", os.path.basename(IMG2)]
    assert [os.path.basename(f) for f in result[1]["images"]] == ["c.jpg", os.path.basename(IMG1)]


def test_poster_rows_and_columns() -> None:
    """rows is the length of the longest column, columns the number of columns"""
    columns = [{"width": "50%", "images": ["a", "b", "c"]}, {"width": "50%", "images": ["d"]}]
    assert img.poster_rows_and_columns(columns) == (3, 2)


def test_posterize_columns_rescales_images_to_column_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each image is rescaled to the pixel width of its own column, keeping its aspect ratio (IMG1 and IMG6 already share a 4:3 ratio,
    so neither is cropped)"""
    commands: list[str] = []
    monkeypatch.setattr(util, "run_ffmpeg", lambda cmd, *_a, **_k: commands.append(cmd))
    columns = [{"width": "60%", "images": [IMG1]}, {"width": "40%", "images": [IMG6]}]
    img.posterize_columns(columns, out_file=TMP1, gutter=0)
    assert "scale=8000:3600" in commands[0]  # Background canvas
    assert "scale=4800:3600" in commands[0]  # IMG1 (640x480) scaled to 60% of the content width
    assert "scale=3200:2400" in commands[0]  # IMG6 (4000x3000) scaled to 40% of the content width


def test_posterize_columns_default_gutter_is_80px(monkeypatch: pytest.MonkeyPatch) -> None:
    """The gutter between images defaults to 80px; extra_margin_top adds background space above the images on top of it"""
    commands: list[str] = []
    monkeypatch.setattr(util, "run_ffmpeg", lambda cmd, *_a, **_k: commands.append(cmd))
    img.posterize_columns([{"width": "100%", "images": [IMG1]}], out_file=TMP1, extra_margin_top=100)
    assert "scale=800:740" in commands[0]  # 640 + 2*80 wide, 100 (extra top) + 480 + 2*80 tall
    assert "overlay=80:180" in commands[0]  # x = gutter (80), y = extra_margin_top (100) + gutter (80)


def test_short_column_is_padded_with_background(monkeypatch: pytest.MonkeyPatch) -> None:
    """A column shorter than the tallest one is simply left as background below its last image"""
    commands: list[str] = []
    monkeypatch.setattr(util, "run_ffmpeg", lambda cmd, *_a, **_k: commands.append(cmd))
    columns = [{"width": "50%", "images": [IMG3, IMG3]}, {"width": "50%", "images": [IMG1]}]
    img.posterize_columns(columns, out_file=TMP1)
    # The 1st column (2 stacked images) is taller than the 2nd (1 image): the background covers the full height of the poster
    assert "scale=8240:6240" in commands[0]
    assert "overlay=80:80" in commands[0]
    assert "overlay=80:3160" in commands[0]
    assert "overlay=4160:80" in commands[0]  # 2nd column starts where the 1st one (4000 wide + gutter) ends


def test_posterize_columns_no_image_raises() -> None:
    """An error is raised when there is no image to posterize"""
    with pytest.raises(ex.InputError):
        img.posterize_columns([{"width": "100%", "images": []}])


# ------------------------------------------------------------------------------
# Normalizing mismatched aspect ratios by cropping
# ------------------------------------------------------------------------------


def test_common_aspect_ratio() -> None:
    """The ratio shared by most of the images is returned, None when they already all share it"""
    files = [img.ImageFile(IMG1), img.ImageFile(IMG6), img.ImageFile(IMG4)]  # 2 images at 4:3, 1 at ~16:9
    assert img.__common_aspect_ratio__(files) == pytest.approx(640 / 480)
    assert img.__common_aspect_ratio__([img.ImageFile(IMG1), img.ImageFile(IMG6)]) is None


def test_crop_to_ratio() -> None:
    """Returns the largest centered crop of a width x height image that matches a target ratio"""
    assert img.__crop_to_ratio__(3000, 1682, 640 / 480) == (2243, 1682)  # Too wide: the width is cropped
    assert img.__crop_to_ratio__(1682, 3000, 480 / 640) == (1682, 2243)  # Too tall: the height is cropped


def test_posterize_columns_crops_mismatched_ratios_to_the_common_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """An image that doesn't share the ratio shared by most of the poster's images is cropped (centered) to match it before scaling"""
    commands: list[str] = []
    monkeypatch.setattr(util, "run_ffmpeg", lambda cmd, *_a, **_k: commands.append(cmd))
    # IMG1 (640x480) and IMG6 (4000x3000) share a 4:3 ratio; IMG4 (3000x1682, ~16:9) doesn't and gets cropped to 4:3
    img.posterize_columns([{"width": "100%", "images": [IMG1, IMG6, IMG4]}], out_file=TMP1, gutter=0)
    assert "crop=2243:1682" in commands[0]
    assert "crop=640:480" not in commands[0]
    assert "crop=4000:3000" not in commands[0]


def test_posterize_columns_no_crop_when_ratios_already_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """No crop filter is added when every image already shares the same aspect ratio"""
    commands: list[str] = []
    monkeypatch.setattr(util, "run_ffmpeg", lambda cmd, *_a, **_k: commands.append(cmd))
    img.posterize_columns([{"width": "100%", "images": [IMG1, IMG6]}], out_file=TMP1, gutter=0)
    assert "crop=" not in commands[0]


# ------------------------------------------------------------------------------
# YAML description file
# ------------------------------------------------------------------------------


def test_is_yaml() -> None:
    """YAML files are detected by their extension"""
    assert poster.is_yaml("a.yaml")
    assert poster.is_yaml("a.YML")
    assert not poster.is_yaml("a.jpg")


def test_write_yaml_keeps_other_items(tmp_path: Path) -> None:
    """The items of the YAML file that are not the poster are kept, the paths are relative to the file"""
    yaml_file = str(tmp_path / "p.yaml")
    columns = [{"width": "100%", "images": [str(tmp_path / "a.jpg")]}]
    poster.write_yaml(yaml_file, str(tmp_path / "p.jpg"), {"rows": 1, "columns": 1}, columns, {"title": "T", "columns": [], "output": "x"})
    assert yaml.safe_load(Path(yaml_file).read_text(encoding="utf-8")) == {
        "poster": {"output": "p.jpg", "rows": 1, "columns": 1},
        "columns": [{"width": "100%", "images": ["a.jpg"]}],
        "title": "T",
    }


def test_load_yaml_not_a_dict(tmp_path: Path) -> None:
    """A YAML file that is not a dictionary is rejected"""
    yaml_file = tmp_path / "list.yaml"
    yaml_file.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(TypeError):
        poster.load_yaml(str(yaml_file))


def test_main_yaml_invalid(tmp_path: Path) -> None:
    """A YAML file without a non-empty 'columns' list is rejected"""
    yaml_in = tmp_path / "bad.yaml"
    yaml_in.write_text("columns: []", encoding="utf-8")
    with patch.object(sys, "argv", ["imagetool", "poster", "-y", str(yaml_in)]), pytest.raises(SystemExit) as e:
        tools.imagetool()
    assert e.value.code == 1


def test_main_two_yaml_files(tmp_path: Path) -> None:
    """Only one YAML file is accepted"""
    files = [tmp_path / "a.yaml", tmp_path / "b.yml"]
    for f in files:
        f.write_text("columns: [{width: 100%, images: [x.jpg]}]", encoding="utf-8")
    with patch.object(sys, "argv", ["imagetool", "poster", "-i", *map(str, files)]), pytest.raises(SystemExit) as e:
        tools.imagetool()
    assert e.value.code == 2


def test_main_yaml_input(tmp_path: Path) -> None:
    """A poster generated from a YAML file: the columns and their widths are read from it"""
    out_file = str(tmp_path / "from-yaml.jpg")
    yaml_in = tmp_path / "in.yaml"
    columns = [{"width": "60%", "images": [os.path.abspath(IMG1)]}, {"width": "40%", "images": [os.path.abspath(IMG2)]}]
    yaml_in.write_text(yaml.safe_dump({"poster": {"output": out_file}, "columns": columns}), encoding="utf-8")
    with patch.object(sys, "argv", ["imagetool", "poster", "-y", str(yaml_in)]):
        try:
            assert tools.imagetool() is None
        except SystemExit as e:
            assert int(str(e)) == 0
    assert os.path.isfile(out_file)
    written = yaml.safe_load(yaml_in.read_text(encoding="utf-8"))
    assert written["poster"]["rows"] == 1
    assert written["poster"]["columns"] == 2
    assert [c["width"] for c in written["columns"]] == ["60%", "40%"]


def test_main_yaml_in_inputs_with_photos(tmp_path: Path) -> None:
    """A YAML file and photos in -i: the photos are distributed into the columns and written back to the YAML file"""
    yaml_in = tmp_path / "trip.yaml"
    columns = [{"width": "100%", "images": [os.path.abspath(IMG1)]}]
    yaml_in.write_text(yaml.safe_dump({"poster": {}, "columns": columns}), encoding="utf-8")
    with patch.object(sys, "argv", ["imagetool", "poster", "-i", str(yaml_in), IMG2]):
        try:
            assert tools.imagetool() is None
        except SystemExit as e:
            assert int(str(e)) == 0
    content = yaml.safe_load(yaml_in.read_text(encoding="utf-8"))
    image_name = content["poster"]["output"]
    assert image_name == "trip.jpg"
    assert os.path.isfile(tmp_path / image_name)
    assert [os.path.basename(i) for i in content["columns"][0]["images"]] == [os.path.basename(IMG1), os.path.basename(IMG2)]
