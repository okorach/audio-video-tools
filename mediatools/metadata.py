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

# This scripts add metadata to a video file
# Encodable data is
# - Year of video
# - Copyright notice
# - Languages of audio tracks
# - Author of video

"""Tool that adds metadata to video files"""

import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil


def main() -> None:
    """Adds metadata (author, year, copyright, language of the audio tracks...) to video files"""
    parser = util.get_common_args("video-metadata", "Tool to add metadata to media files")
    parser.add_argument("--copyright", required=False, help="Copyright string without (c) sign")
    parser.add_argument("--author", required=False, help="Author of the media file")
    parser.add_argument("--year", required=False, help="Year the media file was produced")
    parser.add_argument("--default_track", required=False, type=int, help="Default track")
    parser.add_argument(
        "--language", required=False, nargs="+", help='Languages of tracks, eg "0:fre:Francais sans sous-title" "1:eng:English with music"'
    )
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.VIDEO_FILE)

    def process(inputfile: str, options: dict) -> None:
        """Adds metadata to one video file"""
        if fil.is_video_file(inputfile):
            output = video.VideoFile(inputfile).add_metadata(**options)
            util.generated_file(output)
        else:
            raise ValueError(f"File {inputfile} is not a video file")

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
