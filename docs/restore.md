<!--
media-tools
Copyright (C) 2019-2026 Olivier Korach
mailto:olivier.korach AT gmail DOT com

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
-->

# Backups and `--restore`

The tools that modify a file in place keep the former one as a backup, next to it:

| Tool | Backup | When |
|---|---|---|
| `audiotool volume` / `videotool volume` ([volume](audiotool-volume.md)) | `<file>.before_volume.<ext>` | `--normalize` |
| `videotool rotate` ([rotate](videotool-rotate.md)) | `<file>.before_r<angle>.<ext>` | `--keepName` |
| `videotool flip` ([flip](videotool-flip.md)) | `<file>.before_flip_<direction>.<ext>` | `--keepName` |
| `audiotool denoise` ([denoise](audiotool-denoise.md)) | `<file>.before-denoise.<ext>` | `--keepName` |

No backup is ever overwritten: the next backups of a file, whatever the tool, are numbered (`<file>.before_r90.2.<ext>`, `.3`...) in the order
of the modifications. When a tool processes a directory, the backups it contains are ignored.

## Undoing the modifications

```bash
videotool rotate -i E:\Videos --restore
videotool flip -i clip.mp4 --restore
audiotool volume -i E:\Musique --restore
audiotool denoise -i interview.mp3 --restore
```

`--restore` undoes the modifications made by that tool: each modified file is removed and replaced by its former version, renamed from its
backup (content and dates unchanged). It looks for the backups in the input directories (recursively), or next to the input files.

- All the modifications of the tool are undone, in reverse order: the latest backup first, down to the first one.
- A modification followed by one of another tool can't be undone before it. For instance after a rotation then a flip, run `flip --restore`,
  then `rotate --restore`. Otherwise the command tells which backup is in the way and exits with code 1.
- Former versions of the tools didn't number the backups: if a file has 2 such backups whose order is unknown (eg `.before_r90` and
  `.before_r180`), it is not modified: rename the backups yourself.
- Any change made to a file after its modification is lost with the modified file.
- A file that can't be restored is logged, the others are still restored, and the command exits with code 1.
- Only the files made in place have backups: the other generated files (eg `<file>.r90.<ext>` without `--keepName`) are not removed.
