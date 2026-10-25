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
