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

"""This script rotates videos clockwise of -90, 90, 180 or 270 degrees"""

import mediatools.options as opt
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil


def main() -> None:
    parser = util.get_common_args("video-rotate", "Rotates videos clockwise")
    parser.add_argument(
        "--angle",
        required=False,
        type=int,
        choices=opt.ROTATION_ANGLES,
        default=opt.DEFAULT_ROTATION_ANGLE,
        help=f"Clockwise rotation angle in degrees: {', '.join(str(a) for a in opt.ROTATION_ANGLES)} (-90 is the same as 270), "
        f"{opt.DEFAULT_ROTATION_ANGLE} by default",
    )
    parser.add_argument("--" + opt.Option.VCODEC, required=False, help="Video codec (h264, h265, mpeg2, xvid...)")
    video.add_quality_arg(parser)
    parser.add_argument(
        "-r", "--" + opt.Option.FPS, required=False, help="Video framerate of the output eg 25 (default: the one of the original video)"
    )
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.VIDEO_FILE)

    def process(input_file: str, options: dict) -> None:
        keep_name = options.pop("keepName", False)
        util.generated_file(video.rotate(input_file, options.pop(util.OUTPUT_FILE, None), options.pop("angle"), keep_name, **options))

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
