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

"""Interactive local web app to design a poster: load images from the browser, pick a layout or template, crop each image to a
standard print ratio, drag them around to reorder, tune the gutter/background/title stripe and visualize the result on small
rescaled copies, then save the poster in full quality together with its YAML description (see mediatools.poster)"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import tempfile
import threading
import webbrowser
from dataclasses import dataclass

from flask import Flask, Response, jsonify, request
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

import mediatools.imagefile as image
import mediatools.poster_templates as templates
import mediatools.utilities as util
import utilities.file as fil
from mediatools import log, poster

# Aspect ratios (width / height) a photo can be cropped to in the app, named as they are shown in the UI
CROP_RATIOS: dict[str, float] = {
    "4:3": 4 / 3,
    "3:4": 3 / 4,
    "15:10": 15 / 10,
    "10:15": 10 / 15,
    "16:10": 16 / 10,
    "16:9": 16 / 9,
}

PREVIEW_MAX_DIM: int = 700
THUMB_MAX_DIM: int = 180
DEFAULT_PORT: int = 5151

_ASSET_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poster_webapp.html")


@dataclass
class _PosterItem:
    """One photo of the poster being designed: its full resolution source (the file uploaded from the browser), a small
    rescaled copy used to render the fast preview, and the crop ratio chosen for it in the app (None keeps its own ratio)"""

    item_id: str
    source: str
    preview_source: str
    ratio_key: str | None = None


@dataclass
class _PosterDirs:
    """The directories of a poster design session: where uploaded photos are saved, and the caches of their rescaled preview
    and cropped copies"""

    uploads: str
    preview_cache: str
    full_cache: str


@dataclass
class _PosterLayout:
    """How a session's first batch of images is laid out into columns: a named template, an explicit number of columns (either
    one fixes the grid upfront), or an orientation hint for the fully automatic layout (see mediatools.imagefile.auto_poster_columns).
    Once the first batch is placed into columns, template/cols_count/orientation no longer have any effect"""

    template: str | None = None
    cols_count: int | None = None
    orientation: str | None = None


@dataclass
class _PosterAppState:
    """The state of a poster design session: its photos (items, added from the browser), their grouping into columns (each
    column a list of item ids, top to bottom), the poster settings, the starting layout and the directories used to store the
    uploaded photos and to cache their rescaled/cropped copies"""

    items: dict[str, _PosterItem]
    columns: list[dict]
    settings: dict
    dirs: _PosterDirs
    default_output: str
    layout: _PosterLayout


def _crop_box(width: int, height: int, ratio: float) -> tuple[int, int, int, int]:
    """Returns the (left, top, right, bottom) box of the largest centered crop of a width x height image matching ratio"""
    if width / height > ratio:
        cropped_w, cropped_h = round(height * ratio), height
    else:
        cropped_w, cropped_h = width, round(width / ratio)
    left, top = (width - cropped_w) // 2, (height - cropped_h) // 2
    return left, top, left + cropped_w, top + cropped_h


def _cache_path(cache_dir: str, *parts: str) -> str:
    """Returns the cached file for a photo derivative (a resized copy or a crop), named after a hash of its parts"""
    key = hashlib.md5("|".join(parts).encode("utf-8"), usedforsecurity=False).hexdigest()
    return os.path.join(cache_dir, f"{key}.jpg")


def _make_derivative(src: str, out: str, transform) -> str:
    """Applies transform to the (EXIF-righted) image at src and saves it as out, unless out is already cached. Returns out"""
    if not os.path.isfile(out):
        with Image.open(src) as img:
            transform(ImageOps.exif_transpose(img)).convert("RGB").save(out, "JPEG", quality=88)
    return out


def _make_resized_copy(src: str, cache_dir: str, max_dim: int) -> str:
    """Returns a copy of src rescaled to fit max_dim x max_dim, cached in cache_dir"""
    out = _cache_path(cache_dir, src, str(os.path.getmtime(src)), f"resize{max_dim}")

    def _resize(img: Image.Image) -> Image.Image:
        img = img.copy()
        img.thumbnail((max_dim, max_dim))
        return img

    return _make_derivative(src, out, _resize)


def _make_cropped_copy(src: str, cache_dir: str, ratio_key: str) -> str:
    """Returns a copy of src center-cropped to the ratio named ratio_key, cached in cache_dir"""
    out = _cache_path(cache_dir, src, str(os.path.getmtime(src)), f"crop{ratio_key}")
    ratio = CROP_RATIOS[ratio_key]
    return _make_derivative(src, out, lambda img: img.crop(_crop_box(*img.size, ratio)))


def _resolved_image(item: _PosterItem, *, full_res: bool, cache_dir: str) -> str:
    """Returns the file to feed into the poster for one item: the full resolution source or its rescaled preview copy, cropped
    to its chosen ratio when it has one"""
    base = item.source if full_res else item.preview_source
    return _make_cropped_copy(base, cache_dir, item.ratio_key) if item.ratio_key else base


def _resolved_columns(state: _PosterAppState, *, full_res: bool, cache_dir: str | None = None) -> list[dict]:
    """Returns the poster's columns (as expected by mediatools.imagefile.posterize_columns) resolved to actual image files.
    cache_dir overrides where a full resolution crop is saved (see _save route); it is otherwise the session's own cache"""
    cache_dir = cache_dir or (state.dirs.full_cache if full_res else state.dirs.preview_cache)
    return [
        {"width": col["width"], "images": [_resolved_image(state.items[i], full_res=full_res, cache_dir=cache_dir) for i in col["images"]]}
        for col in state.columns
    ]


def _image_count(state: _PosterAppState) -> int:
    """Returns the total number of images currently placed in the poster's columns"""
    return sum(len(col["images"]) for col in state.columns)


def _template_image_count(state: _PosterAppState) -> int | None:
    """Returns the number of images the session's template requires, None when no template is used"""
    return templates.TEMPLATES[state.layout.template].image_count if state.layout.template else None


def _update_state(state: _PosterAppState, body: dict) -> None:
    """Applies the columns ordering, crop ratios and settings received from the browser to the session state. Raises ValueError
    if the request refers to an unknown item"""
    columns = body.get("columns") or []
    for col in columns:
        for item_id in col.get("images", []):
            if item_id not in state.items:
                raise ValueError(f"Unknown image {item_id}")
    if columns:
        state.columns = [{"width": col.get("width") or f"{100 / len(columns):g}%", "images": col["images"]} for col in columns]
    for item_id, ratio_key in (body.get("ratios") or {}).items():
        if item_id not in state.items:
            raise ValueError(f"Unknown image {item_id}")
        if ratio_key and ratio_key not in CROP_RATIOS:
            raise ValueError(f"Unknown ratio {ratio_key}")
        state.items[item_id].ratio_key = ratio_key or None
    settings = body.get("settings") or {}
    for key in ("background_color", "gutter", "extra_margin_top", "extra_margin_bottom"):
        if settings.get(key) not in (None, ""):
            state.settings[key] = settings[key]


def _state_to_json(state: _PosterAppState) -> dict:
    """Returns the session state as sent to the browser: the items (with a small embedded thumbnail), the columns and the settings"""
    thumbs = {}
    for item_id, item in state.items.items():
        thumb = _make_resized_copy(item.source, state.dirs.preview_cache, THUMB_MAX_DIM)
        with open(thumb, "rb") as f:
            thumbs[item_id] = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")
    return {
        "items": {i: {"thumb": thumbs[i], "ratio_key": it.ratio_key} for i, it in state.items.items()},
        "columns": state.columns,
        "settings": state.settings,
        "ratios": list(CROP_RATIOS),
        "default_output": state.default_output,
        "max_images": _template_image_count(state),
        "orientation": state.layout.orientation,
        "orientation_locked": bool(state.layout.cols_count or state.columns),
    }


def _render_preview(state: _PosterAppState) -> str | None:
    """Renders the poster on the rescaled preview copies of the photos. Returns it as a data: URL, None if there is no image yet"""
    if not _image_count(state):
        return None
    columns = _resolved_columns(state, full_res=False)
    out = os.path.join(state.dirs.preview_cache, "preview.jpg")
    image.posterize_columns(columns, out_file=out, **state.settings)
    with open(out, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")


def _unique_path(directory: str, filename: str) -> str:
    """Returns a path for filename in directory that doesn't collide with an existing file, numbering it if needed"""
    base, ext = os.path.splitext(filename)
    candidate, n = os.path.join(directory, filename), 1
    while os.path.isfile(candidate):
        candidate = os.path.join(directory, f"{base}-{n}{ext}")
        n += 1
    return candidate


def _add_item(state: _PosterAppState, saved_path: str) -> str:
    """Adds a newly uploaded photo as a new item of the session. Returns its id"""
    item_id = f"img-{len(state.items)}"
    state.items[item_id] = _PosterItem(item_id, saved_path, _make_resized_copy(saved_path, state.dirs.preview_cache, PREVIEW_MAX_DIM))
    return item_id


def _place_new_items(state: _PosterAppState, new_ids: list[str], new_paths: list[str]) -> None:
    """Places newly added items into the poster's columns: round-robin into the existing columns when there are some, into
    cols_count new (empty) columns when a layout/template fixes their number, or laid out automatically from the images
    themselves (see mediatools.imagefile.auto_poster_columns) when this is the very first batch of a fully automatic poster"""
    if not state.columns:
        if state.layout.cols_count:
            width = f"{100 / state.layout.cols_count:g}%"
            state.columns = [{"width": width, "images": []} for _ in range(state.layout.cols_count)]
        else:
            path_columns = image.auto_poster_columns(*new_paths, orientation=state.layout.orientation)
            path_to_id = dict(zip(new_paths, new_ids, strict=True))
            state.columns = [{"width": col["width"], "images": [path_to_id[p] for p in col["images"]]} for col in path_columns]
            return
    order = sorted(range(len(state.columns)), key=lambda i: len(state.columns[i]["images"]))
    for i, item_id in enumerate(new_ids):
        state.columns[order[i % len(state.columns)]]["images"].append(item_id)


def create_app(state: _PosterAppState) -> Flask:
    """Creates the Flask app that serves the poster design page and its JSON API"""
    app = Flask(__name__)

    @app.route("/")
    def _index() -> Response:
        with open(_ASSET_FILE, encoding="utf-8") as f:
            html = f.read()
        return Response(html.replace("__INITIAL_STATE__", json.dumps(_state_to_json(state))), mimetype="text/html")

    @app.route("/api/upload", methods=["POST"])
    def _upload() -> tuple[Response, int] | Response:
        files = request.files.getlist("images")
        if not files:
            return jsonify({"error": "No file given"}), 400
        orientation = request.form.get("orientation") or None
        if orientation not in (None, "portrait", "landscape"):
            return jsonify({"error": f"Unknown orientation {orientation}"}), 400
        if not state.columns and not state.layout.cols_count:
            state.layout.orientation = orientation
        max_images = _template_image_count(state)
        if max_images is not None and _image_count(state) + len(files) > max_images:
            return jsonify({"error": f"Template '{state.layout.template}' accepts at most {max_images} images"}), 400
        accepted_ext = fil.FileType.FILE_EXTENSIONS[fil.FileType.IMAGE_FILE]
        new_ids, new_paths = [], []
        for f in files:
            name = secure_filename(f.filename or "photo")
            if "." not in name or name.rsplit(".", 1)[-1].lower() not in accepted_ext:
                return jsonify({"error": f"{f.filename} is not a supported image type"}), 400
            saved_path = _unique_path(state.dirs.uploads, name)
            f.save(saved_path)
            new_paths.append(saved_path)
            new_ids.append(_add_item(state, saved_path))
        _place_new_items(state, new_ids, new_paths)
        return jsonify(_state_to_json(state))

    @app.route("/api/preview", methods=["POST"])
    def _preview() -> tuple[Response, int] | Response:
        try:
            _update_state(state, request.get_json(force=True) or {})
            return jsonify({"preview": _render_preview(state)})
        except (ValueError, KeyError) as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/save", methods=["POST"])
    def _save() -> tuple[Response, int] | Response:
        try:
            body = request.get_json(force=True) or {}
            _update_state(state, body)
            if not _image_count(state):
                return jsonify({"error": "No image loaded yet"}), 400
            output = body.get("output") or state.default_output
            crops_dir = fil.strip_extension(os.path.abspath(output)) + "_crops"
            os.makedirs(crops_dir, exist_ok=True)
            columns = _resolved_columns(state, full_res=True, cache_dir=crops_dir)
            out_path = image.posterize_columns(columns, out_file=output, **state.settings)
        except (ValueError, KeyError) as e:
            return jsonify({"error": str(e)}), 400
        yaml_file = fil.strip_extension(out_path) + ".yaml"
        rows_count, cols_count = image.poster_rows_and_columns(columns)
        yaml_settings = {"rows": rows_count, "columns": cols_count, **state.settings}
        if state.layout.template:
            yaml_settings["template"] = state.layout.template
        poster.write_yaml(yaml_file, out_path, {k: v for k, v in yaml_settings.items() if v}, columns)
        util.generated_file(out_path)
        log.logger.info("Poster description written to %s", yaml_file)
        return jsonify({"output": out_path, "yaml": yaml_file})

    return app


def _cache_dirs() -> _PosterDirs:
    """Creates and returns the (uploads, preview cache, full resolution cache) directories of a new session, in the OS default
    temp directory"""
    cache_root = tempfile.mkdtemp(prefix="poster-webapp-")
    dirs = _PosterDirs(*(os.path.join(cache_root, name) for name in ("uploads", "preview", "full")))
    for directory in (dirs.uploads, dirs.preview_cache, dirs.full_cache):
        os.makedirs(directory, exist_ok=True)
    return dirs


def _build_empty_state(*, template: str | None, layout: str | None, orientation: str | None = None) -> _PosterAppState:
    """Builds a new, empty session: no photo yet, laid out with the template or layout given (or fully automatically, in the
    orientation given, once the first photos are loaded from the browser) once photos are added (see _place_new_items)"""
    template_defaults: dict = {}
    if template:
        template_defaults = templates.defaults(templates.TEMPLATES[template])
        layout = layout or template_defaults["layout"]
    cols_count = int(layout.split("x")[1]) if layout else None

    settings = {
        "background_color": template_defaults.get("background_color", "black"),
        "gutter": template_defaults.get("gutter", 80),
        "extra_margin_top": template_defaults.get("extra_margin_top", 0),
        "extra_margin_bottom": template_defaults.get("extra_margin_bottom", 0),
    }
    default_output = os.path.join(os.getcwd(), "poster.jpg")
    return _PosterAppState({}, [], settings, _cache_dirs(), default_output, _PosterLayout(template, cols_count, orientation))


def __add_webapp_args__(parser: argparse.ArgumentParser) -> None:
    """Adds the options of the poster web app to the parser"""
    parser.add_argument(
        "--template",
        required=False,
        choices=sorted(templates.TEMPLATES),
        help="Named poster template to start from (see 'imagetool poster --help'). The app then accepts at most as many images "
        "as the template's grid",
    )
    parser.add_argument("-l", "--layout", required=False, help="Layout of the images to start from: rows x columns, eg 2x3")
    parser.add_argument(
        "--orientation",
        required=False,
        choices=["portrait", "landscape"],
        help="Orientation of the poster (no --template/--layout): default picks whichever of the 2 standard printing formats "
        "(70/50 or 50/70) best fits the first images loaded. Can also be picked in the app before the first image is loaded",
    )
    parser.add_argument("--host", required=False, default="127.0.0.1", help="Address the local web server listens on")
    parser.add_argument("--port", required=False, type=int, default=DEFAULT_PORT, help="Port of the local web server")
    parser.add_argument("--no-browser", required=False, action="store_true", help="Don't automatically open the web browser")


def main() -> None:
    """Starts the local web app to interactively design a poster: the images are loaded from the browser, not from the command
    line"""
    util.init("poster-webapp")
    parser = argparse.ArgumentParser(description="Interactive web app to design a poster: load images, layout, crop, reorder, tune and preview it")
    util.add_verbosity_arg(parser)
    __add_webapp_args__(parser)
    kwargs = vars(parser.parse_args())
    util.set_debug_level(kwargs.get("verbosity"))

    state = _build_empty_state(template=kwargs.get("template"), layout=kwargs.get("layout"), orientation=kwargs.get("orientation"))
    app = create_app(state)

    url = f"http://{kwargs['host']}:{kwargs['port']}/"
    if not kwargs.get("no_browser"):
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    log.logger.info("Poster web app listening on %s", url)
    app.run(host=kwargs["host"], port=kwargs["port"], threaded=False)


if __name__ == "__main__":
    main()
