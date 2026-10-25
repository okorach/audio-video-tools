# videotool flip

Flips videos: swaps their left and right (default), or their top and bottom.

```
videotool flip -i <files and/or directories> [--direction leftright|topbottom] [--quality high|medium|low] [--fps <fps>] [--resolution <WxH>] [--vcodec <codec>] [--hw_accel auto|on|off] [--keepName] [-o <output>]
```

| Option | Description |
|---|---|
| `-i` | Videos and/or directories (processed recursively). Several files are processed in a loop |
| `--direction` | `leftright` (default) swaps the left and the right of the video, as in a mirror. `topbottom` swaps the top and the bottom |
| `--quality` | Video quality `high` (default), `medium` or `low`, see [quality.md](quality.md) |
| `--fps` | Frame rate of the output. Default: the one of the original video |
| `--resolution` | Resolution of the output (aliases accepted, see [resolutions.md](resolutions.md)). Default: the one of the original video |
| `--vcodec` | Video codec. Default: the codec of the original video |
| `--hw_accel` | `auto` (default), `on` or `off`, see [hw-accel.md](hw-accel.md). The GPU encodes the video, the flip itself is done by the CPU. In `auto` mode, the CPU is used if the command fails with the GPU |
| `--keepName` | The output has the name of the original video, which is renamed `<original>.before_flip_<direction>.<ext>` |
| `-o` | Output file (a single input file only, not with `--keepName`) |
| `-v` | Verbosity of the logs, see [verbosity.md](verbosity.md) |

By default the output file is `<original>.flip_<direction>.<ext>`, for instance `video.flip_leftright.mp4` or `video.flip_topbottom.mp4`.
The audio tracks are kept and the output file gets the dates of the original video, see [metadata-preservation.md](metadata-preservation.md).
