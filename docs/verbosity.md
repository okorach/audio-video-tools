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

# Verbosity of the logs

All the tools accept the `-v` (or `--verbosity`) option, that sets the level of the logs displayed on the console and written in the log file of the tool (`<tool>.log`):

`-v CRITICAL|ERROR|WARNING|INFO|DEBUG`

- The level is case insensitive (`-v debug` is the same as `-v DEBUG`).
- `INFO` is the default.
- `-g <0 to 4>` (the former option, with an integer level, from 0 = `CRITICAL` to 4 = `DEBUG`) is still accepted but deprecated.

For instance: `videotool slideshow -i <directory> -v DEBUG`.
