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

# imagetool poster-webapp

Starts a local web app in the browser to interactively design a [poster](imagetool-poster.md): load images from the browser, pick a
layout or [template](imagetool-poster.md#templates), crop each image to a standard print ratio, drag images around to reorder them,
tune the gutter, background color and title stripe, and visualize the result live on small, quickly-rendered copies of the images.
Once the result looks right, save it: the full resolution poster and its YAML description (the same format as `imagetool poster`) are
written to disk.

```
imagetool poster-webapp [--template <name>] [--layout <rows>x<cols>] [--host <address>] [--port <port>] [--no-browser]
```

| Option | Description |
|---|---|
| `--template` | A named template to start from (see [imagetool poster](imagetool-poster.md#templates)). The app then accepts at most as many images as the template's grid |
| `-l`, `--layout` | Number of rows x columns (eg `2x3`) to start from, instead of the usual automatic layout (picked once the first images are loaded) |
| `--host` | Address the local web server listens on. Default: `127.0.0.1` |
| `--port` | Port of the local web server. Default: `5151` |
| `--no-browser` | Don't automatically open the web browser |

## Using the app

The **Load images** panel picks images from the browser's own file picker (no path to type); each one is added to the poster. With
no `--template`/`--layout`, the layout is picked automatically from the first batch of images loaded (see `imagetool poster`); more
images can be loaded afterwards, added round-robin into the existing columns. With a template, loading more images than its grid
needs is rejected.

Each column of the poster is shown as a vertical list of its images. An image can be:

- **Reordered**: drag it up/down within its column, or across to another column.
- **Cropped**: pick one of `4:3`, `3:4`, `15:10`, `10:15`, `16:10` or `16:9` in its dropdown (or `original` to keep its own aspect
  ratio). The crop is centered.

The side panel tunes the poster's `background_color`, `gutter` and `extra_margin_top`/`extra_margin_bottom` (eg for a title stripe),
exactly as the matching options of `imagetool poster`. Every change re-renders the preview on small, rescaled copies of the images, so
it stays fast regardless of the size of the originals.

Clicking **Save poster + YAML** renders the poster at the full resolution of the loaded images, at the output path given, and writes
its YAML description next to it (default: `poster.jpg`/`poster.yaml` in the current directory). A cropped image is saved as a new
file; an image left as `original` is referenced directly, as `imagetool poster` would.

## Example

```bash
imagetool poster-webapp --template landscape40-4x3
```

Opens the app on the `landscape40-4x3` template's grid (4 rows x 3 columns, 12 images), ready for images to be loaded, cropped,
reordered and tuned before saving.

## Batch file

`batch-files-images/poster.bat` runs `imagetool poster` (the CLI version) on the images dragged onto it; run with no images dragged
onto it (eg double-clicked), it opens the web app instead, where images are loaded from the browser.
