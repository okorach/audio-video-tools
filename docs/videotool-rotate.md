# videotool rotate

Rotates videos clockwise.

```
videotool rotate -i <files and/or directories> [--angle -90|90|180|270] [--quality high|medium|low] [--fps <fps>] [--resolution <WxH>] [--vcodec <codec>] [--hw_accel auto|on|off] [--keepName] [-o <output>]
```

| Option | Description |
|---|---|
| `-i` | Videos and/or directories (processed recursively). Several files are processed in a loop |
| `--angle` | Clockwise rotation angle in degrees: `-90`, `90`, `180` or `270` (`-90` is the same as `270`). Any other value is rejected. Default `90` |
| `--quality` | Video quality `high` (default), `medium` or `low`, see [quality.md](quality.md) |
| `--fps` | Frame rate of the output. Default: the one of the original video |
| `--resolution` | Resolution of the output (size after the rotation, aliases accepted, see [resolutions.md](resolutions.md)). Default: the one of the original video, rotated (1920x1080 rotated of 90 degrees is 1080x1920) |
| `--vcodec` | Video codec. Default: the codec of the original video |
| `--hw_accel` | `auto` (default), `on` or `off`, see [hw-accel.md](hw-accel.md). The GPU encodes the video, the rotation itself is done by the CPU. In `auto` mode, the CPU is used if the command fails with the GPU |
| `--keepName` | The output has the name of the original video, which is renamed `<original>.before_r<rotation>.<ext>` |
| `-o` | Output file (a single input file only, not with `--keepName`) |

By default the output file is `<original>.r<rotation>.<ext>`, for instance `video.r90.mp4`, `video.r180.mp4`, `video.r270.mp4`.
