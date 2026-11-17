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

"""Interactive local web app to design a poster: pick images and a layout or template, crop each image to a standard print
ratio, drag them around to reorder, tune the gutter/background/title stripe and visualize the result on small rescaled copies,
then save the poster in full quality together with its YAML description (see mediatools.poster)"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import tempfile
import threading
import webbrowser
from dataclasses import dataclass, field

from flask import Flask, Response, jsonify, request
from PIL import Image, ImageOps

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
    """One photo of the poster being designed: its full resolution source, a small rescaled copy used to render the fast
    preview, and the crop ratio chosen for it in the app (None keeps its original aspect ratio)"""

    item_id: str
    source: str
    preview_source: str
    ratio_key: str | None = None


@dataclass
class _PosterAppState:
    """The state of a poster design session: its photos (items), their grouping into columns (each column a list of item ids,
    top to bottom), the poster settings and the directories used to cache the rescaled/cropped copies of the photos"""

    items: dict[str, _PosterItem]
    columns: list[dict]
    settings: dict
    preview_cache: str
    full_cache: str
    default_output: str
    template: str | None = field(default=None)


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
    cache_dir = cache_dir or (state.full_cache if full_res else state.preview_cache)
    return [
        {"width": col["width"], "images": [_resolved_image(state.items[i], full_res=full_res, cache_dir=cache_dir) for i in col["images"]]}
        for col in state.columns
    ]


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
        thumb = _make_resized_copy(item.source, state.preview_cache, THUMB_MAX_DIM)
        with open(thumb, "rb") as f:
            thumbs[item_id] = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")
    return {
        "items": {i: {"thumb": thumbs[i], "ratio_key": it.ratio_key} for i, it in state.items.items()},
        "columns": state.columns,
        "settings": state.settings,
        "ratios": list(CROP_RATIOS),
        "default_output": state.default_output,
    }


def _render_preview(state: _PosterAppState) -> str:
    """Renders the poster on the rescaled preview copies of the photos. Returns it as a data: URL"""
    columns = _resolved_columns(state, full_res=False)
    out = os.path.join(state.preview_cache, "preview.jpg")
    image.posterize_columns(columns, out_file=out, **state.settings)
    with open(out, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")


def create_app(state: _PosterAppState) -> Flask:
    """Creates the Flask app that serves the poster design page and its JSON API"""
    app = Flask(__name__)

    @app.route("/")
    def _index() -> Response:
        with open(_ASSET_FILE, encoding="utf-8") as f:
            html = f.read()
        return Response(html.replace("__INITIAL_STATE__", json.dumps(_state_to_json(state))), mimetype="text/html")

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
        if state.template:
            yaml_settings["template"] = state.template
        poster.write_yaml(yaml_file, out_path, {k: v for k, v in yaml_settings.items() if v}, columns)
        util.generated_file(out_path)
        log.logger.info("Poster description written to %s", yaml_file)
        return jsonify({"output": out_path, "yaml": yaml_file})

    return app


def _cache_dirs() -> tuple[str, str]:
    """Creates and returns the (preview, full resolution) cache directories of a new session, in the OS default temp directory"""
    cache_root = tempfile.mkdtemp(prefix="poster-webapp-")
    preview_cache, full_cache = os.path.join(cache_root, "preview"), os.path.join(cache_root, "full")
    os.makedirs(preview_cache, exist_ok=True)
    os.makedirs(full_cache, exist_ok=True)
    return preview_cache, full_cache


def _build_items(columns: list[dict], preview_cache: str) -> tuple[dict[str, _PosterItem], list[dict]]:
    """Returns the session's items (one per photo, with its rescaled preview copy) and the columns of their ids, numbered in the
    order of columns"""
    items: dict[str, _PosterItem] = {}
    id_columns: list[dict] = []
    counter = 0
    for col in columns:
        ids = []
        for path in col["images"]:
            item_id = f"img-{counter}"
            counter += 1
            source = os.path.abspath(path)
            items[item_id] = _PosterItem(item_id, source, _make_resized_copy(source, preview_cache, PREVIEW_MAX_DIM))
            ids.append(item_id)
        id_columns.append({"width": col["width"], "images": ids})
    return items, id_columns


def _build_initial_state(parser: argparse.ArgumentParser, photos: list[str], *, template: str | None, layout: str | None) -> _PosterAppState:
    """Builds the initial session state: the photos are laid out with the template or layout given (or the usual automatic
    layout), each starting with no crop. Aborts (via parser.error) if a template is given with the wrong number of images"""
    template_defaults: dict = {}
    if template:
        tmpl = templates.TEMPLATES[template]
        if len(photos) != tmpl.image_count:
            parser.error(f"Template '{template}' requires exactly {tmpl.image_count} images ({tmpl.layout}), got {len(photos)}")
        template_defaults = templates.defaults(tmpl)
        layout = layout or template_defaults["layout"]

    layout_kwargs = {"layout": layout} if layout else {}
    columns = image.auto_poster_columns(*photos, **layout_kwargs)
    preview_cache, full_cache = _cache_dirs()
    items, id_columns = _build_items(columns, preview_cache)

    settings = {
        "background_color": template_defaults.get("background_color", "black"),
        "gutter": template_defaults.get("gutter", 80),
        "extra_margin_top": template_defaults.get("extra_margin_top", 0),
        "extra_margin_bottom": template_defaults.get("extra_margin_bottom", 0),
    }
    default_output = os.path.join(os.path.dirname(os.path.abspath(photos[0])), "poster.jpg")
    return _PosterAppState(items, id_columns, settings, preview_cache, full_cache, default_output, template)


def __add_webapp_args__(parser: argparse.ArgumentParser) -> None:
    """Adds the options of the poster web app (besides -i) to the parser"""
    parser.add_argument(
        "--template",
        required=False,
        choices=sorted(templates.TEMPLATES),
        help="Named poster template to start from (see 'imagetool poster --help'). Requires exactly as many images as the " "template's grid",
    )
    parser.add_argument("-l", "--layout", required=False, help="Layout of the images to start from: rows x columns, eg 2x3")
    parser.add_argument("--host", required=False, default="127.0.0.1", help="Address the local web server listens on")
    parser.add_argument("--port", required=False, type=int, default=DEFAULT_PORT, help="Port of the local web server")
    parser.add_argument("--no-browser", required=False, action="store_true", help="Don't automatically open the web browser")


def main() -> None:
    """Starts the local web app to interactively design a poster from a set of images"""
    util.init("poster-webapp")
    parser = argparse.ArgumentParser(description="Interactive web app to design a poster: layout, crop, reorder, tune and preview it, then save it")
    util.add_input_args(parser, "Images and/or directories to use in the poster")
    util.add_verbosity_arg(parser)
    __add_webapp_args__(parser)
    kwargs = vars(parser.parse_args())
    util.set_debug_level(kwargs.get("verbosity"))

    photos = fil.file_list(*kwargs[util.INPUT_FILES], file_type=fil.FileType.IMAGE_FILE)
    if not photos:
        parser.error("No image found in the input")

    state = _build_initial_state(parser, photos, template=kwargs.get("template"), layout=kwargs.get("layout"))
    app = create_app(state)

    url = f"http://{kwargs['host']}:{kwargs['port']}/"
    if not kwargs.get("no_browser"):
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    log.logger.info("Poster web app listening on %s", url)
    app.run(host=kwargs["host"], port=kwargs["port"], threaded=False)


if __name__ == "__main__":
    main()
