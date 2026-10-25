# Video quality

The video encoding tools (`videotool encode`, `profile-encode`...) accept `--quality high|medium|low`, which is a better way than a bitrate to control the quality of the encoded video: the encoder spends the bits where the video needs them.

The quality is mapped to the constant quality option of the video encoder (`-crf` for the CPU encoders, `-cq` for the hardware accelerated ones):

| Quality | x264 (h264) | x265 (h265) |
|---|---|---|
| `high` | 18 | 23 |
| `medium` | 23 | 28 |
| `low` | 28 | 33 |

- When neither `--quality` nor a video bitrate (`--vbitrate`, or the bitrate of the profile) is given, the quality is `high`.
- When a video bitrate is given without `--quality`, the bitrate is used, as before.
- When `--quality` is given, it is used instead of the bitrate.
- The quality is not used when the video is copied, nor for the codecs without constant quality mode.

For instance: `videotool encode -i <file> --vcodec x265 --width 1920 --quality medium`.
