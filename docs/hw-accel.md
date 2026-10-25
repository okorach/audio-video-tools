# Hardware acceleration (`--hw_accel`)

The tools that decode or encode videos can use the Nvidia hardware acceleration (CUDA decoding, NVENC encoding).
Every tool that runs ffmpeg has the `--hw_accel` option:

| Value | Behavior |
|-------|----------|
| `auto` (default) | The hardware acceleration is used when it's available. If a command fails with it, the tool tries again with the CPU |
| `on` | The hardware acceleration is always used, a failure is an error |
| `off` | The CPU is always used |

The default can be changed with the `default.hw_accel` property of `~/.mediatools.properties`.

## Auto mode

- The availability of the hardware acceleration is checked once per run, by encoding a few frames of a test video with
  NVENC. If it's not available (no Nvidia GPU, missing driver), the CPU is used and nothing is retried.
- When it's available, every ffmpeg command that decodes and encodes video uses it: `videotool profile-encode`, `encode`, `crop`
  and `concat` (also the concatenation of the parts of a long `slideshow`).
- If such a command fails (a source format the GPU can't decode, a resolution or a filter the encoder doesn't support...),
  a warning is logged and the whole operation is run again on the CPU, so that the result is the same as with `--hw_accel off`.
  The operation is only run again if a hardware accelerated command was run, so a failure that has nothing to do with the GPU
  (a missing file, an invalid option) is reported at once.
- Deinterlacing (`--deinterlace`) is not compatible with the hardware acceleration: the CPU is used in auto mode.

## Tools

`videotool slideshow` uses the GPU to encode the video of each photo and the final slideshow (`h264_nvenc`). The filters
(zoom, pan, cross-fades) run on the CPU, and so does the decoding of the clips, as decoding some of them on the GPU and the others on
the CPU fails. If a command fails with the GPU in auto mode, the whole slideshow is made again on the CPU.

`videotool rotate` and `flip` use the GPU to encode the rotated or flipped video (`h264_nvenc` or `hevc_nvenc`, like the codec of the original video). The
rotation and the flip are CPU filters, so the video is decoded on the CPU. If the command fails with the GPU in auto mode, it is run again on the CPU.

The operations that always use the CPU don't use the hardware acceleration whatever the option: video filters that run on the
CPU only (`videotool reverse`, `speed`, `stabilize` and the `enhance` color filters), the copy of streams
(`videotool cut`, `mux` and `metadata`), and the image and audio tools. They accept the option so that the same command line
works with all the tools.

## In the code

`util.hw_accel_fallback` decorates the functions that run hardware accelerated commands (`VideoFile.encode`, `VideoFile.crop`,
`concat`, `slideshow`): they get the `hw_accel` mode in their arguments and test `util.use_hardware_accel(**kwargs)` to build
their command. `util.get_hw_accel_mode()` returns the mode (`auto`, `on` or `off`).
