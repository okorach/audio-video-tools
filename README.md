# media-tools
Python and (legacy) Perl based batch tools to transcode audio and video conveniently (leverages FFMpeg)

The `-i` option of the tools accepts files and directories (processed recursively): see [docs/input-files.md](docs/input-files.md).

The tools use the Nvidia hardware acceleration when it's available, with a fallback to the CPU if a command fails with it: see [docs/hw-accel.md](docs/hw-accel.md).
