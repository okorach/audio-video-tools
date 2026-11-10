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

# videotool slideshow

Creates a high quality video slideshow from photos and/or video clips: each photo becomes a short clip with a slow zoom or panorama effect, each
video clip is scaled and cropped (centered) to fill the resolution and stripped of its soundtrack (a slideshow has none), the clips are cross-faded
into each other, and the video fades in and out.

```
videotool slideshow -i <photos, video clips and/or directories> [-o <output>] [--resolution <WxH or alias>] [--fps <fps>] [--quality high|medium|low] [--hw_accel auto|on|off]
videotool slideshow -i <file.yaml> [<more photos or video clips>] [same options]
```

| Option | Description |
|---|---|
| `-i` | Photos, video clips and/or directories (processed recursively), and/or one YAML file (`.yaml` or `.yml`) describing the slideshow. The photos and video clips given with a YAML file are added at the end of the slideshow |
| `-y`, `--yaml` | Same as giving the YAML file in `-i` |
| `-o` | Output video. Default: the `output` of the YAML file, else the name of the YAML file (or of the first input) with the video extension |
| `--resolution` | Resolution of the video (aliases accepted, see [resolutions.md](resolutions.md)). Default: `default.slideshow.resolution` (3840x2160) |
| `--fps` | Frame rate of the video. Default: `default.slideshow.fps` (50) |
| `--quality` | Video quality `high` (default), `medium` or `low`, see [quality.md](quality.md) |
| `--hw_accel` | `auto` (default), `on` or `off`, see [hw-accel.md](hw-accel.md) |

A YAML file describing the slideshow is generated next to the video. Its `slideshow` section holds the general parameters (`output`, `resolution`, `fps`, `quality`) and
`photos` the effect of each photo or video clip (its `photo` key is kept for a video clip too, for backward compatibility). The paths are relative to the YAML file.

The clip generated from each photo is a temporary file named after its settings (photo, resolution, fps, quality, effect, zoom level or vertical drift, duration),
in the OS default temp directory. Regenerating the same slideshow (eg from its YAML file) reuses a clip already generated with the same settings instead of
re-encoding it. A video clip's slide is always regenerated (no reuse), keeping the whole clip's own duration unless the YAML file gives it an explicit one.

When a YAML file is given in `-i`, it is the description of the slideshow, in the format below. The options of the command line take precedence over the settings of the file, and the file is not modified for them.
The YAML file is updated in place: the photos and video clips added in `-i` are appended to its `photos`, and the generated video is set in `slideshow.output` if the file had none.
