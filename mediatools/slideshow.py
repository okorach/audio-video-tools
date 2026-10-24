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

import yaml
from mediatools import log
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil


def main():
    parser = util.get_common_args("slideshow", "Creates a high quality video slide show from a set of photos")
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.IMAGE_FILE)

    output, operations = video.slideshow(
        *kwargs["inputfiles"], outfile=kwargs.get("outputfile"), resolution=kwargs.get("resolution"), hw_accel=kwargs.get("hw_accel", "auto")
    )

    yaml_file = fil.strip_extension(output) + ".yaml"
    with open(yaml_file, "w", encoding="utf-8") as f:
        yaml.safe_dump({"output": output, "photos": operations}, f, sort_keys=False, default_flow_style=False)

    log.logger.info("Slide show description written to %s", yaml_file)
    util.generated_file(output)


if __name__ == "__main__":
    main()
