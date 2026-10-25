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

import mediatools.utilities as util
import mediatools.options as opt
import mediatools.videofile as video
import utilities.file as fil


def main():
    parser = util.get_common_args("video-reverse", "Reverse a video")
    parser.add_argument(
        "-k", "--keep_audio", required=False, dest=opt.Option.MUTE, action="store_false", default=True, help="Keep audio track after reverse"
    )
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.VIDEO_FILE)

    def process(input_file: str, options: dict) -> None:
        util.generated_file(video.reverse(input_file, options.pop(util.OUTPUT_FILE, None), **options))

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
