# Verbosity of the logs

All the tools accept the `-v` (or `--verbosity`) option, that sets the level of the logs displayed on the console and written in the log file of the tool (`<tool>.log`):

`-v CRITICAL|ERROR|WARNING|INFO|DEBUG`

- The level is case insensitive (`-v debug` is the same as `-v DEBUG`).
- `INFO` is the default.
- `-g <0 to 4>` (the former option, with an integer level, from 0 = `CRITICAL` to 4 = `DEBUG`) is still accepted but deprecated.

For instance: `videotool slideshow -i <directory> -v DEBUG`.
