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

# Resolutions

The `--resolution` (`-s`) option of the tools, and the `--box` option of `videotool crop`, accept a size as `<width>x<height>` or one of these aliases (case insensitive):

| Aliases | Resolution |
|---|---|
| `4k`, `2160p` | 3840x2160 |
| `2.7k`, `1520p` | 2704x1520 |
| `2.5k`, `1440p` | 2560x1440 |
| `fhd`, `1080p` | 1920x1080 |
| `hd`, `720p` | 1280x720 |
| `540p`, `400p`, `360p`, `vga`, `xga` | 960x540, 720x400, 640x360, 640x480, 1024x768 |

For instance: `videotool slideshow -i <directory> --resolution 4k`.
