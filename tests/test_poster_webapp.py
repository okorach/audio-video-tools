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

"""Tests of the interactive poster web app"""

import argparse
import os

import pytest

import mediatools.poster_webapp as webapp
from mediatools import poster

DIR = "it" + os.sep
PHOTOS = [os.path.abspath(DIR + f) for f in ("img-640x480.jpg", "img-640x480-2.jpg", "img-3000x1682.jpg", "img-4000x3000.jpg")]


def _state(layout: str | None = "2x2", template: str | None = None, photos: list[str] | None = None) -> webapp._PosterAppState:
    """Builds an initial session state for the given photos (PHOTOS by default)"""
    return webapp._build_initial_state(argparse.ArgumentParser(), photos or PHOTOS, template=template, layout=layout)


def test_crop_box_landscape_source() -> None:
    """A wider-than-target image is cropped on its width, keeping the full height"""
    assert webapp._crop_box(400, 300, 1.0) == (50, 0, 350, 300)


def test_crop_box_portrait_source() -> None:
    """A narrower-than-target image is cropped on its height, keeping the full width"""
    assert webapp._crop_box(300, 400, 1.0) == (0, 50, 300, 350)


def test_build_initial_state_layout() -> None:
    """The initial state has one item per photo, grouped into the requested layout, with no crop chosen"""
    state = _state(layout="2x2")
    assert len(state.items) == len(PHOTOS)
    assert len(state.columns) == 2
    assert all(item.ratio_key is None for item in state.items.values())
    assert state.settings["background_color"] == "black"


def test_build_initial_state_template_sets_defaults() -> None:
    """A template sets its own layout, background color, gutter and title stripe"""
    photos = PHOTOS * 3  # landscape40-4x3 needs 12 images
    state = _state(layout=None, template="landscape40-4x3", photos=photos)
    assert len(state.columns) == 3
    assert state.settings["background_color"] == "black"
    assert state.settings["extra_margin_bottom"] == webapp.templates.TITLE_STRIPE
    assert state.template == "landscape40-4x3"


def test_build_initial_state_template_aborts_on_wrong_count() -> None:
    """Building the initial state aborts when the number of photos doesn't match the template's grid"""
    with pytest.raises(SystemExit):
        _state(layout=None, template="landscape40-4x3", photos=PHOTOS[:2])


def test_index_page_embeds_state() -> None:
    """The index page is served with the session's items embedded in it"""
    state = _state()
    client = webapp.create_app(state).test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert next(iter(state.items)) in body


def test_preview_renders_and_reflects_settings() -> None:
    """A preview request renders a poster and applies the settings sent along with it"""
    state = _state()
    client = webapp.create_app(state).test_client()
    item_id = next(iter(state.items))
    resp = client.post(
        "/api/preview",
        json={"columns": state.columns, "ratios": {item_id: "4:3"}, "settings": {"background_color": "white", "gutter": "5%"}},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["preview"].startswith("data:image/jpeg;base64,")
    assert state.items[item_id].ratio_key == "4:3"
    assert state.settings["background_color"] == "white"
    assert state.settings["gutter"] == "5%"


def test_preview_rejects_unknown_item() -> None:
    """A preview request for an image id that doesn't belong to the session is rejected"""
    state = _state()
    client = webapp.create_app(state).test_client()
    resp = client.post("/api/preview", json={"columns": [{"width": "100%", "images": ["does-not-exist"]}]})
    assert resp.status_code == 400


def test_preview_rejects_unknown_ratio() -> None:
    """A preview request with an unsupported crop ratio is rejected"""
    state = _state()
    client = webapp.create_app(state).test_client()
    item_id = next(iter(state.items))
    resp = client.post("/api/preview", json={"columns": state.columns, "ratios": {item_id: "1:1"}})
    assert resp.status_code == 400


def test_save_writes_poster_and_yaml(tmp_path) -> None:
    """Saving writes the poster at the requested resolution and a YAML description reflecting the final layout and settings"""
    state = _state()
    client = webapp.create_app(state).test_client()
    columns = [{"width": col["width"], "images": list(reversed(col["images"]))} for col in state.columns]
    output = str(tmp_path / "my-poster.jpg")
    resp = client.post(
        "/api/save",
        json={"columns": columns, "settings": {"background_color": "white", "gutter": "10%"}, "output": output},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert os.path.isfile(data["output"])
    assert os.path.isfile(data["yaml"])
    params, yaml_columns = poster.read_yaml(data["yaml"])
    assert params["background_color"] == "white"
    assert params["gutter"] == "10%"
    assert sum(len(col["images"]) for col in yaml_columns) == len(PHOTOS)


def test_save_persists_crops_next_to_output(tmp_path) -> None:
    """A cropped image is saved as a real file next to the output, not left in the session's temporary cache"""
    state = _state()
    client = webapp.create_app(state).test_client()
    item_id = next(iter(state.items))
    output = str(tmp_path / "my-poster.jpg")
    resp = client.post("/api/save", json={"columns": state.columns, "ratios": {item_id: "4:3"}, "output": output})
    assert resp.status_code == 200
    crops_dir = tmp_path / "my-poster_crops"
    assert crops_dir.is_dir()
    assert any(crops_dir.iterdir())


def test_save_rejects_unknown_item(tmp_path) -> None:
    """Saving with an image id that doesn't belong to the session is rejected"""
    state = _state()
    client = webapp.create_app(state).test_client()
    resp = client.post(
        "/api/save",
        json={"columns": [{"width": "100%", "images": ["nope"]}], "output": str(tmp_path / "out.jpg")},
    )
    assert resp.status_code == 400
