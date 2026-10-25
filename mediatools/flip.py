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

"""This script flips videos: it swaps their left and right (default), or their top and bottom"""

import mediatools.options as opt
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil


def main() -> None:
    """Flips videos: swaps their left and right, or their top and bottom"""
    parser = util.get_common_args("video-flip", "Flips videos (swaps the left and the right, or the top and the bottom)")
    parser.add_argument(
        "--direction",
        required=False,
        type=str.lower,
        choices=opt.FLIP_DIRECTIONS,
        default=opt.DEFAULT_FLIP_DIRECTION,
        help=f"Direction of the flip: {' or '.join(opt.FLIP_DIRECTIONS)} (swaps the left and the right, or the top and the bottom), "
        f"{opt.DEFAULT_FLIP_DIRECTION} by default",
    )
    video.add_reencode_args(parser)
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.VIDEO_FILE)

    def process(input_file: str, options: dict) -> None:
        """Flips one video"""
        keep_name = options.pop("keepName", False)
        util.generated_file(video.flip(input_file, options.pop(util.OUTPUT_FILE, None), options.pop("direction"), keep_name, **options))

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
