<!--
  media-tools
  Copyright (C) 2019-2026 Olivier Korach
  mailto:olivier.korach AT gmail DOT com

  This program is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 3 of the License, or (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public License
  along with this program; if not, write to the Free Software Foundation,
  Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
-->

# media-tools
Python and (legacy) Perl based batch tools to transcode audio and video conveniently (leverages FFMpeg)

The tools are also available as actions of 4 unified commands (`videotool`, `audiotool`, `imagetool` and `pdftool`): see [docs/unified-commands.md](docs/unified-commands.md).

The `-i` option of the tools accepts files and directories (processed recursively): see [docs/input-files.md](docs/input-files.md).

The tools use the Nvidia hardware acceleration when it's available, with a fallback to the CPU if a command fails with it: see [docs/hw-accel.md](docs/hw-accel.md).

The verbosity of the logs is set with `-v CRITICAL|ERROR|WARNING|INFO|DEBUG` (`INFO` by default): see [docs/verbosity.md](docs/verbosity.md).

The quality of the encoded videos is set with `--quality high|medium|low` (`high` by default), a better option than the bitrate: see [docs/quality.md](docs/quality.md). The format of the generated videos is set with `--format`: see [docs/format.md](docs/format.md).

The resolutions can be given as `<width>x<height>` or as an alias (`4k`, `2.7k`, `2.5k`, `fhd`, `hd`...): see [docs/resolutions.md](docs/resolutions.md).

Videos can be rotated with `videotool rotate`: see [docs/videotool-rotate.md](docs/videotool-rotate.md).

Slideshows are created with `videotool slideshow` (50 fps by default): see [docs/videotool-slideshow.md](docs/videotool-slideshow.md).

Videos can be flipped (left/right or top/bottom) with `videotool flip`: see [docs/videotool-flip.md](docs/videotool-flip.md).
