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

# imagetool poster

Creates a poster image from several photos, arranged in columns: each column is a vertical stack of its images, scaled to the column's
own width. When the photos don't all share the same aspect ratio, the odd ones out are cropped (centered) to the ratio shared by most
of them, so every photo of the poster ends up the same shape; otherwise each photo keeps its own aspect ratio.

```
imagetool poster -i <photos and/or directories> [-o <output>] [--background_color black|white] [--margin <px or %>]
                  [--extra_margin_top <px>] [--extra_margin_bottom <px>] [--orientation portrait|landscape] [--aspect_ratio <W/H or W:H>]
                  [--layout <rows>x<cols>] [--hw_accel auto|on|off]
imagetool poster -i <file.yaml> [<more photos>] [same options]
```

| Option | Description |
|---|---|
| `-i` | Photos and/or directories (processed recursively), and/or one YAML file (`.yaml` or `.yml`) describing the poster. Photos given with a YAML file are distributed into its columns, round-robin, starting with the shortest column |
| `-y`, `--yaml` | Same as giving the YAML file in `-i` |
| `-o` | Output image. Default: the `output` of the YAML file, else the name of the YAML file (or of the first photo) with the image extension |
| `-b`, `--background_color` | `black` (default) or `white`: the color of the margins and of the padding under a column shorter than the tallest one |
| `-m`, `--margin` | Margin between the images: a number of pixels (eg `64px`), or a percentage of the width of the top-left image (eg `5%`). Default: `50px` |
| `--extra_margin_top` | Extra margin (pixels) of background color above the images, eg to overlay a title. Default: 0 |
| `--extra_margin_bottom` | Extra margin (pixels) of background color below the images. Default: 0 |
| `--orientation` | `portrait` or `landscape`: used, with `--aspect_ratio`, to pick the number of columns when the poster is generated from a flat list of photos (no YAML, no `--layout`) |
| `--aspect_ratio` | Target aspect ratio of the poster, eg `4/3`, `16:9` or `1.3333`, used the same way as `--orientation`. Default: `70/50`, the most common poster printing format |
| `--layout` | Number of rows x columns (eg `2x3`), used instead of `--orientation`/`--aspect_ratio` to pick the number of columns when there is no YAML |
| `--hw_accel` | `auto` (default), `on` or `off`, see [hw-accel.md](hw-accel.md) |

When the poster is generated from a flat list of photos, with no `--orientation`, `--aspect_ratio` nor `--layout`, the number of columns
is picked so that the poster approximates the most common poster printing format (70/50 or 50/70 cm), in whichever of the 2 orientations
best fits the photos (landscape if they are mostly landscape, portrait otherwise).

A YAML file describing the poster is generated next to the image. Its `poster` section holds the global parameters (`output`, `rows`,
`columns`, `background_color`, `margin`, `extra_margin_top`, `extra_margin_bottom`, `orientation`, `aspect_ratio`), and `columns` the
list of its columns, each with a `width` (a percentage of the poster's content width, excluding the margins) and the list of its
`images`. The paths are relative to the YAML file. By default, when the poster is generated from a flat list of photos, every column
gets an equal share of the width (50% each for 2 columns, 33.33% for 3, 25% for 4...) and the photos are distributed into the columns
round-robin; editing the YAML file lets a column be given a different width, or a different set of images.

When a YAML file is given in `-i`, it is the description of the poster, in the format above. The options of the command line take
precedence over the settings of the file, and the file is not modified for them. The YAML file is updated in place: the photos added
in `-i` are distributed into its columns, and the generated poster is set in `poster.output` if the file had none.

A column shorter than the tallest one is padded with the background color at the bottom, so the columns stay aligned at the top.

## Example

```yaml
poster:
  output: trip.jpg
  rows: 3
  columns: 2
  background_color: black
  margin: 5%
  extra_margin_top: 120
  orientation: landscape
columns:
  - width: 50%
    images:
      - photo1.jpg
      - photo3.jpg
      - photo5.jpg
  - width: 50%
    images:
      - photo2.jpg
      - photo4.jpg
```
