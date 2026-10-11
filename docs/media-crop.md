# media-crop

Crops a region of a video. The output has the same codec and container as the source, a video bitrate
proportional to the cropped area, and audio tracks (and other streams) copied unchanged.

## Usage

```
media-crop -i <input> [-o <output>] [--box <W>x<H>|4k|fhd|1k|hd] [--top|--center|--bottom] [--left|--right] [--hw_accel auto|on|off] [-g <level>]
```

| Option | Description |
|--------|-------------|
| `-i`, `--inputfiles` | Video to crop |
| `-o`, `--outputfile` | Output file. Default: `<input>.crop_<W>x<H>-<position>.<ext>` |
| `--box <W>x<H>` | Size of the cropped region. Default `1920x1080`. Aliases (case insensitive): `4k` = 3840x2160, `fhd` or `1k` = 1920x1080, `hd` = 1280x720 |
| `--top`, `--center`, `--bottom` | Vertical alignment of the region in the source |
| `--left`, `--right` | Horizontal alignment of the region in the source |
| `--hw_accel` | Nvidia hardware acceleration: `auto` (default), `on`, `off` |
| `-g` | Debug level |

Vertical and horizontal options can be combined: `--top --left` aligns the region with the top left corner
of the source. `--center` alone, or no position at all, centers the region. A direction that is not given
is centered (eg `--top` crops at the top center).

## Video bitrate

The output video bitrate is the source bitrate multiplied by the ratio of the cropped area to the source
area. Cropping 1280x720 out of a 1920x1080 30 Mbit/s video (44%) gives a ~13.3 Mbit/s output.

## Errors

If the box is wider or taller than the source video, the command logs an error and exits with code 1.
Conflicting positions (eg `--top --bottom`) or a malformed `--box` exit with code 2.

## Examples

```
# Crop the 1280x720 top left corner of the source video
media-crop -i foo.mp4 --box 1280x720 --top --left

# Crop a 1920x1080 region at the center of the source video
media-crop -i foo.mp4 --box 1920x1080 --center

# Crop a 4K region at the top left of an 8K source
media-crop -i foo.mp4 --box 4k --top --left

# Crop a portrait 720x1280 region at the bottom center of the source video
media-crop -i foo.mp4 --box 720x1280 --bottom --center
```
