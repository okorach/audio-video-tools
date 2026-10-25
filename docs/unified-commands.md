# Unified commands

The tools are also available as actions of 4 commands, which are followed by the action and the parameters of this action:

| Command | Works on | Actions |
|---|---|---|
| `videotool` | videos | `crop`, `concat`, `cut`, `deshake`, `encode`, `encodeauto`, `enhance`, `metadata`, `mirror`, `mux`, `profile-encode`, `reverse`, `rotate`, `slideshow`, `snap`, `specs`, `speed`, `stabilize`, `volume` |
| `audiotool` | audio files | `album-art`, `concat`, `cut`, `denoise`, `encode`, `fix-mp3-meta`, `lib`, `list`, `normalize`, `profile-encode`, `specs`, `speed`, `split`, `volume` |
| `imagetool` | images | `blinds`, `crop-ratio`, `poster`, `scale`, `shake`, `specs`, `stack`, `to-video` |
| `pdftool` | PDF files | `compress`, `merge`, `split` |

For instance: `videotool crop -i <file> --box 1920x1080 --center`.

- `<command>` alone, or `<command> -h`, lists the actions. `<command> <action> -h` shows the parameters of the action.
- The parameters of an action are the ones of the corresponding tool, `-i` included (files and directories).
- `profile-encode` encodes with an encoding profile (`-p`), `encode` is the ffmpeg front-end encoder.
- `linker`, `renamer`, `datefixer` and `shuffle` are not about a single kind of file and have their own commands.
