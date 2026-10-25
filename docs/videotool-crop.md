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

# videotool crop

Crops a region of a video. The output has the same codec and container as the source, a video bitrate
proportional to the cropped area, and audio tracks (and other streams) copied unchanged.

## Usage

```
videotool crop -i <input> [-o <output>] [--box <W>x<H>|4k|fhd|1k|hd] [--top|--center|--bottom] [--left|--right] [--hw_accel auto|on|off] [-v CRITICAL|ERROR|WARNING|INFO|DEBUG]
```

| Option | Description |
|--------|-------------|
| `-i`, `--inputfiles` | Video to crop |
| `-o`, `--outputfile` | Output file. Default: `<input>.crop.<ext>` (`foo.mp4` gives `foo.crop.mp4`) |
| `--box <W>x<H>` | Size of the cropped region. Default `1920x1080`. Aliases (case insensitive): `4k` = 3840x2160, `fhd` or `1k` = 1920x1080, `hd` = 1280x720 |
| `--top`, `--center`, `--bottom` | Vertical alignment of the region in the source |
| `--left`, `--right` | Horizontal alignment of the region in the source |
| `--topleft`, `--topright`, `--bottomleft`, `--bottomright` | Shortcuts for `--top --left`, `--top --right`, `--bottom --left` and `--bottom --right` |
| `--hw_accel` | Nvidia hardware acceleration: `auto` (default), `on`, `off` |
| `-v`, `--verbosity` | Verbosity of the logs: `CRITICAL`, `ERROR`, `WARNING`, `INFO` (default) or `DEBUG` |

Vertical and horizontal options can be combined: `--top --left` aligns the region with the top left corner
of the source. `--center` alone, or no position at all, centers the region. A direction that is not given
is centered (eg `--top` crops at the top center).

## Video bitrate

The output video bitrate is the source bitrate multiplied by the ratio of the cropped area to the source
area. Cropping 1280x720 out of a 1920x1080 30 Mbit/s video (44%) gives a ~13.3 Mbit/s output.

## Rotated videos and streams

- Videos recorded with a rotation flag (eg a 3840x2880 video with a 90 degrees rotation, displayed as 2880x3840)
  are cropped relative to the displayed frame: the box and the position apply to the video as you see it in a player.
- Only the main video stream is re-encoded. Other video streams (eg embedded thumbnails), audio and subtitle streams are copied.
  Data streams (eg camera telemetry) are dropped because the container can't always hold them.

## Creation date

Once encoded, the creation date metadata of the output file is set to the creation date of the source video.

## Errors

If the box is wider or taller than the source video, the command logs an error and exits with code 1.
Conflicting positions (eg `--top --bottom`) or a malformed `--box` exit with code 2.

## Examples

```
# Crop the 1280x720 top left corner of the source video
videotool crop -i foo.mp4 --box 1280x720 --top --left
# Same, with the corner shortcut
videotool crop -i foo.mp4 --box 1280x720 --topleft

# Crop a 1920x1080 region at the center of the source video
videotool crop -i foo.mp4 --box 1920x1080 --center

# Crop a 4K region at the top left of an 8K source
videotool crop -i foo.mp4 --box 4k --top --left

# Crop a portrait 720x1280 region at the bottom center of the source video
videotool crop -i foo.mp4 --box 720x1280 --bottom --center
```
