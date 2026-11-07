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

# Format of the generated videos

The tools that generate a video accept `--format <mp4|avi|mkv|...>` to choose the format (container) of the generated file: `videotool encode`, `profile-encode`, `rotate`, `flip`, `speed`, `reverse`, `enhance`, `deshake`, `stabilize`, `crop`, `cut` and `slideshow`.

- By default, the format is the one of the original file.
- When an output file is given (`-o`), the format is deduced from its extension (and `--format` is ignored).
- When the format is different from the one of the original file, the generated file is named `<original basename>.<format>` and the original file is left as is, even with `--keepName` (nothing is renamed `.original`).
- When the format is the one of the original file, the generated file is named `<original basename>.<postfix>.<format>` as usual (`.r90`, `.flip_leftright`, `.color`...).

For instance: `videotool rotate -i movie.avi --format mp4` generates `movie.mp4`.
