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

# Unified commands

The tools are also available as actions of 4 commands, which are followed by the action and the parameters of this action:

| Command | Works on | Actions |
|---|---|---|
| `videotool` | videos | `crop`, `concat`, `cut`, `deshake`, `encode`, `encodeauto`, `enhance`, `flip`, `metadata`, `mux`, `profile-encode`, `reverse`, `rotate`, `slideshow`, `snap`, `specs`, `speed`, `stabilize`, `volume` |
| `audiotool` | audio files | `album-art`, `concat`, `cut`, `denoise`, `encode`, `fix-mp3-meta`, `lib`, `list`, `normalize`, `profile-encode`, `specs`, `speed`, `split`, `volume` |
| `imagetool` | images | `blinds`, `crop-ratio`, `poster`, `scale`, `shake`, `specs`, `stack`, `to-video` |
| `pdftool` | PDF files | `compress`, `merge`, `split` |

For instance: `videotool crop -i <file> --box 1920x1080 --center`.

- `<command>` alone, or `<command> -h`, lists the actions. `<command> <action> -h` shows the parameters of the action.
- The parameters of an action are the ones of the corresponding tool, `-i` included (files and directories).
- `profile-encode` encodes with an encoding profile (`-p`), `encode` is the ffmpeg front-end encoder.
- `linker`, `renamer`, `datefixer` and `shuffle` are not about a single kind of file and have their own commands.
