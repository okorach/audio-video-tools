# media-tools
Python and (legacy) Perl based batch tools to transcode audio and video conveniently (leverages FFMpeg)

The tools are also available as actions of 4 unified commands (`videotool`, `audiotool`, `imagetool` and `pdftool`): see [docs/unified-commands.md](docs/unified-commands.md).

The `-i` option of the tools accepts files and directories (processed recursively): see [docs/input-files.md](docs/input-files.md).

The tools use the Nvidia hardware acceleration when it's available, with a fallback to the CPU if a command fails with it: see [docs/hw-accel.md](docs/hw-accel.md).

The verbosity of the logs is set with `-v CRITICAL|ERROR|WARNING|INFO|DEBUG` (`INFO` by default): see [docs/verbosity.md](docs/verbosity.md).

The quality of the encoded videos is set with `--quality high|medium|low` (`high` by default), a better option than the bitrate: see [docs/quality.md](docs/quality.md).

The resolutions can be given as `<width>x<height>` or as an alias (`4k`, `2.7k`, `2.5k`, `fhd`, `hd`...): see [docs/resolutions.md](docs/resolutions.md).
