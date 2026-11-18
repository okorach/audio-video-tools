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

"""Tests of the interactive poster web app: images are loaded from the browser (file upload), not from the command line"""

import os
from contextlib import ExitStack

from flask.testing import FlaskClient

import mediatools.poster_webapp as webapp
from mediatools import poster

DIR = "it" + os.sep
PHOTOS = [DIR + f for f in ("img-640x480.jpg", "img-640x480-2.jpg", "img-3000x1682.jpg", "img-4000x3000.jpg")]


def _client(template: str | None = None, layout: str | None = None, orientation: str | None = None) -> tuple[FlaskClient, webapp._PosterAppState]:
    """Returns a (Flask test client, state) pair for a fresh, empty session"""
    state = webapp._build_empty_state(template=template, layout=layout, orientation=orientation)
    return webapp.create_app(state).test_client(), state


def _upload(client: FlaskClient, photos: list[str] = PHOTOS) -> dict:
    """Uploads photos (by path) to the session and returns the JSON response"""
    with ExitStack() as stack:
        data = {"images": [(stack.enter_context(open(p, "rb")), os.path.basename(p)) for p in photos]}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
    return resp, resp.get_json()


def _set_layout(client: FlaskClient, orientation: str | None = None, aspect_ratio: str | None = None) -> dict:
    """Sets the session's orientation and/or aspect ratio hint and returns the JSON response"""
    resp = client.post("/api/layout", json={"orientation": orientation, "aspect_ratio": aspect_ratio})
    return resp, resp.get_json()


def test_crop_box_landscape_source() -> None:
    """A wider-than-target image is cropped on its width, keeping the full height"""
    assert webapp._crop_box(400, 300, 1.0) == (50, 0, 350, 300)


def test_crop_box_portrait_source() -> None:
    """A narrower-than-target image is cropped on its height, keeping the full width"""
    assert webapp._crop_box(300, 400, 1.0) == (0, 50, 300, 350)


def test_empty_session_has_no_image() -> None:
    """A fresh session starts with no image and no column"""
    _, state = _client()
    assert not state.items
    assert not state.columns
    assert state.settings["background_color"] == "black"


def test_template_sets_defaults_and_cols_count() -> None:
    """A template sets its own column count, background color, gutter and title stripe before any image is loaded"""
    _, state = _client(template="landscape40-4x3")
    assert state.layout.cols_count == 3
    assert state.settings["extra_margin_bottom"] == webapp.templates.TITLE_STRIPE
    assert state.layout.template == "landscape40-4x3"


def test_upload_with_no_layout_picks_one_automatically() -> None:
    """The first batch of uploaded images picks the layout automatically, like imagetool poster does with no --layout"""
    client, state = _client()
    resp, body = _upload(client)
    assert resp.status_code == 200
    assert len(body["items"]) == len(PHOTOS)
    assert len(state.columns) >= 1
    assert sum(len(col["images"]) for col in state.columns) == len(PHOTOS)


def test_layout_orientation_overrides_automatic_layout() -> None:
    """A portrait orientation set before any image is loaded picks a narrower grid than the automatic (landscape-leaning) default"""
    client, state = _client()
    _set_layout(client, orientation="portrait")
    _upload(client)
    assert len(state.columns) == 1


def test_layout_rejects_unknown_orientation() -> None:
    """Setting an orientation that isn't portrait or landscape is rejected"""
    client, _ = _client()
    resp, body = _set_layout(client, orientation="sideways")
    assert resp.status_code == 400
    assert "sideways" in body["error"]


def test_layout_rejects_unknown_aspect_ratio() -> None:
    """Setting an aspect ratio that isn't one of the app's named ratios is rejected"""
    client, _ = _client()
    resp, body = _set_layout(client, aspect_ratio="1:1")
    assert resp.status_code == 400
    assert "1:1" in body["error"]


def test_layout_is_ignored_once_a_layout_is_fixed() -> None:
    """A fixed layout (or template) decides the number of columns; an orientation sent alongside it has no effect"""
    client, state = _client(layout="2x2")
    _, body = _set_layout(client, orientation="portrait")
    _upload(client)
    assert len(state.columns) == 2
    assert state.layout.orientation is None
    assert body["layout_locked"] is True


def test_changing_orientation_relayouts_images_already_loaded() -> None:
    """Changing the orientation after images are already loaded recomputes the columns from all of them, not just new ones"""
    client, state = _client()
    _upload(client)
    assert len(state.columns) >= 2
    _, body = _set_layout(client, orientation="portrait")
    assert len(state.columns) == 1
    assert sum(len(col["images"]) for col in state.columns) == len(PHOTOS)
    assert body["layout_locked"] is False


def test_changing_aspect_ratio_relayouts_images_already_loaded() -> None:
    """Changing the aspect ratio after images are already loaded recomputes the columns from all of them"""
    client, state = _client()
    _upload(client)
    cols_before = len(state.columns)
    _set_layout(client, aspect_ratio="9:16")
    assert state.layout.aspect_ratio == "9:16"
    assert len(state.columns) != cols_before
    assert sum(len(col["images"]) for col in state.columns) == len(PHOTOS)


def test_upload_with_layout_places_round_robin() -> None:
    """With a fixed layout, uploaded images are placed round-robin into that many columns"""
    client, state = _client(layout="2x2")
    _upload(client)
    assert len(state.columns) == 2
    assert [len(col["images"]) for col in state.columns] == [2, 2]


def test_upload_twice_appends_to_existing_columns() -> None:
    """A second batch of images is appended into the columns already laid out by the first one"""
    client, state = _client(layout="1x2")
    _upload(client, PHOTOS[:2])
    _upload(client, PHOTOS[2:])
    assert len(state.columns) == 2
    assert sum(len(col["images"]) for col in state.columns) == len(PHOTOS)


def test_upload_rejects_exceeding_template_count() -> None:
    """Uploading more images than a template's grid needs is rejected"""
    client, _ = _client(template="landscape40-2x2")  # 4 images
    resp, body = _upload(client, [*PHOTOS, DIR + "img-2320x4000.jpg"])  # 5 images
    assert resp.status_code == 400
    assert "landscape40-2x2" in body["error"]


def test_upload_rejects_non_image_file(tmp_path) -> None:
    """Uploading a file that isn't a supported image type is rejected"""
    client, _ = _client()
    not_an_image = tmp_path / "notes.txt"
    not_an_image.write_text("hello")
    with open(not_an_image, "rb") as f:
        resp = client.post("/api/upload", data={"images": [(f, "notes.txt")]}, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_index_page_embeds_state() -> None:
    """The index page is served with the session's items (once loaded) embedded in it"""
    client, state = _client()
    _upload(client)
    resp = client.get("/")
    assert resp.status_code == 200
    assert next(iter(state.items)) in resp.get_data(as_text=True)


def test_preview_is_empty_before_any_image() -> None:
    """There is no preview to render before any image is loaded"""
    client, _ = _client()
    resp = client.post("/api/preview", json={})
    assert resp.status_code == 200
    assert resp.get_json()["preview"] is None


def test_preview_renders_and_reflects_settings() -> None:
    """A preview request renders a poster and applies the settings sent along with it"""
    client, state = _client()
    _upload(client)
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
    client, _ = _client()
    resp = client.post("/api/preview", json={"columns": [{"width": "100%", "images": ["does-not-exist"]}]})
    assert resp.status_code == 400


def test_preview_rejects_unknown_ratio() -> None:
    """A preview request with an unsupported crop ratio is rejected"""
    client, state = _client()
    _upload(client)
    item_id = next(iter(state.items))
    resp = client.post("/api/preview", json={"columns": state.columns, "ratios": {item_id: "1:1"}})
    assert resp.status_code == 400


def test_save_rejects_when_no_image_loaded(tmp_path) -> None:
    """Saving before any image is loaded is rejected"""
    client, _ = _client()
    resp = client.post("/api/save", json={"output": str(tmp_path / "out.jpg")})
    assert resp.status_code == 400


def test_save_writes_poster_and_yaml(tmp_path) -> None:
    """Saving writes the poster at the requested resolution and a YAML description reflecting the final layout and settings"""
    client, state = _client()
    _upload(client)
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
    client, state = _client()
    _upload(client)
    item_id = next(iter(state.items))
    output = str(tmp_path / "my-poster.jpg")
    resp = client.post("/api/save", json={"columns": state.columns, "ratios": {item_id: "4:3"}, "output": output})
    assert resp.status_code == 200
    crops_dir = tmp_path / "my-poster_crops"
    assert crops_dir.is_dir()
    assert any(crops_dir.iterdir())


def test_save_rejects_unknown_item(tmp_path) -> None:
    """Saving with an image id that doesn't belong to the session is rejected"""
    client, _ = _client()
    _upload(client)
    resp = client.post(
        "/api/save",
        json={"columns": [{"width": "100%", "images": ["nope"]}], "output": str(tmp_path / "out.jpg")},
    )
    assert resp.status_code == 400
