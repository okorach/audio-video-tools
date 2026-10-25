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

import argparse
import mediatools.utilities as util
import mediatools.audiofile as audio
import utilities.file as fil


def main() -> None:
    """Concatenates audio files into a single audio file"""
    util.init("audio-concat")
    parser = argparse.ArgumentParser(description="Concatenates several audio files of the same type")
    util.add_input_args(parser, "List of audio files to concatenate")
    util.add_output_args(parser, "Output file to generate", required=True)
    util.add_verbosity_arg(parser)
    util.add_hw_accel_arg(parser)
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.AUDIO_FILE)
    output = audio.concat(kwargs[util.OUTPUT_FILE], kwargs[util.INPUT_FILES])
    util.generated_file(output)


if __name__ == "__main__":
    main()
