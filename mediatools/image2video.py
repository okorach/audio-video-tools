#!python3
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

import sys
from mediatools import log
import mediatools.utilities as util
import mediatools.exceptions as ex
import mediatools.imagefile as image
import mediatools.media_config as conf


def main():
    parser = util.get_common_args("image2video", "Converts an image to a video")
    parser.add_argument("--style", required=True, choices=["zoom", "panorama"], default="zoom", help="Effect to generate")
    parser.add_argument("--bounds", required=False, help="bounds of the panorama or zoom")
    parser.add_argument("--speed", required=False, type=float, help="Panorama or zoom speed")
    parser.add_argument("--vspeed", required=False, type=float, default=0, help="Panorama or zoom vertical speed")
    parser.add_argument("--duration", required=False, type=float, help="Panorama or zoom duration")
    kwargs = util.parse_media_args(parser)

    inputfile = kwargs.pop("inputfiles")[0]
    resolution = kwargs.get("resolution", conf.get_property("default.video.resolution"))
    kwargs.pop("resolution")

    if kwargs.get("bounds", None) is not None:
        kwargs["effect"] = [float(x) for x in kwargs["bounds"].split(",")]

    try:
        if kwargs.pop("style", "zoom") == "panorama":
            output = image.ImageFile(inputfile).panorama(resolution=resolution, **kwargs)
        else:
            output = image.ImageFile(inputfile).zoom(resolution=resolution, **kwargs)
    except ex.InputError as e:
        log.logger.critical(e.message)
        print("ERROR: {}", e.message)
        sys.exit(ex.InputError("Missing args", "image2video"))
    util.generated_file(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
