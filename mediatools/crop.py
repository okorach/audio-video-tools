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

# This scripts crops a region of a video file
# --box <width>x<height> or 4k, fhd, 1k, hd : The size of the region to crop (default 1920x1080)
# --top, --center, --bottom, --left, --right: Where in the source video the region is taken (default centered)
# --topleft, --topright, --bottomleft, --bottomright: Shortcuts for --top --left, --top --right, --bottom --left, --bottom --right

import re
import sys
import subprocess
from mediatools import log
from mediatools import creator
import mediatools.videofile as video
import mediatools.utilities as util
import utilities.file as fil

POSITIONS = ("top", "center", "bottom", "left", "right")
# Corner shortcuts, each is the equivalent of the 2 options it is made of (eg --topleft is --top --left)
CORNERS = {"topleft": ("top", "left"), "topright": ("top", "right"), "bottomleft": ("bottom", "left"), "bottomright": ("bottom", "right")}


def main() -> None:
    """Entry point of the media-crop command"""
    parser = util.get_common_args("media-crop", "Crops a region of the input video file")
    parser.add_argument(
        "--box",
        required=False,
        default=video.DEFAULT_CROP_BOX,
        help="Size of the cropped region: <width>x<height> eg 1280x720, or 4k (3840x2160), fhd or 1k (1920x1080), hd (1280x720). Default 1920x1080",
    )
    parser.add_argument("--top", required=False, default=False, action="store_true", help="Crop region is aligned with the top of the source")
    parser.add_argument("--center", required=False, default=False, action="store_true", help="Crop region is centered in the source")
    parser.add_argument("--bottom", required=False, default=False, action="store_true", help="Crop region is aligned with the bottom of the source")
    parser.add_argument("--left", required=False, default=False, action="store_true", help="Crop region is aligned with the left of the source")
    parser.add_argument("--right", required=False, default=False, action="store_true", help="Crop region is aligned with the right of the source")
    for corner, (vertical, horizontal) in CORNERS.items():
        parser.add_argument(f"--{corner}", required=False, default=False, action="store_true", help=f"Same as --{vertical} --{horizontal}")
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.VIDEO_FILE)

    selected = {p for p in POSITIONS if kwargs.pop(p, False)}
    for corner, parts in CORNERS.items():
        if kwargs.pop(corner, False):
            selected.update(parts)
    position = " ".join(p for p in POSITIONS if p in selected)
    if re.search(r"top.*bottom|left.*right", position):
        log.logger.error("Incompatible crop positions: %s", position)
        sys.exit(2)
    # --top, --left, etc... are position hints, not ffmpeg options
    kwargs["position"] = position or "center"
    try:
        kwargs["width"], kwargs["height"] = video.parse_crop_box(kwargs.pop("box"))
    except ValueError as e:
        log.logger.error("Invalid --box value: %s", str(e))
        sys.exit(2)
    log.logger.debug("KW=%s", str(kwargs))

    def process(input_file: str, options: dict) -> None:
        try:
            outputfile = creator.file(input_file).crop(out_file=options.pop("outputfile", None), **options)
        except (ValueError, subprocess.CalledProcessError) as e:
            raise ValueError(f"Crop failed: {e}") from e
        log.logger.info("Generated %s", outputfile)
        print(f"Generated {outputfile}")

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
