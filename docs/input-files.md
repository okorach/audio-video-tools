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

# Input files and directories (`-i`)

The `-i` / `--inputfiles` option of the tools takes a **list of files and/or directories**.
Each directory is replaced by all the files it contains, **recursively**.

```
# file1.mp4, file2.mp4 and all the video files in dir1 (and its sub-directories) are processed
videotool volume -i file1.mp4 file2.mp4 dir1 --volume 200%
```

## Rules

- The arguments are processed in the order given. The files of a directory are in alphabetical order of their paths
  (case insensitive), sub-directories included: `dir1/b.mp4`, `dir1/sub/d.mp4`, `dir1/z.mp4`.
- A file given explicitly is always taken, whatever its type. The tool reports an error if it can't process it.
- In a directory, only the files that the action can process are taken: video files for the `videotool` actions (`crop`,
  `reverse`, `speed`...), image files for the `imagetool` actions (`scale`, `blinds`...), audio files for the `audiotool`
  actions (`speed`...), audio and video files for the actions that handle both (`audiotool denoise`, `volume`, `cut`,
  `profile-encode`), PDF files for `pdftool`. Actions that handle any kind of media take all the audio, video and image files.
- A directory without any matching file is an error (exit code 1).

## Tools processing each file

`videotool` (`crop`, `cut`, `volume`, `specs`, `reverse`, `speed`, `metadata`, `deshake`, `stabilize`, `enhance`, `snap`,
`profile-encode`, `encode`, `encodeauto`), `audiotool` (`speed`, `split`, `denoise`, `cut`, `volume`, `encode`, `profile-encode`),
`imagetool` (`scale`, `blinds`, `shake`, `to-video`, `crop-ratio`) and `pdftool` (`split`, `compress`):
each file is processed independently, and the output file name is derived from the input file name.

- `-o` can't be used when there are several input files (exit code 2).
- A failure on one file doesn't prevent the next ones from being processed, the exit code is 1 at the end.

## Tools combining the files

`videotool concat` and `mux`, `audiotool concat`, `imagetool stack` and `poster`, `pdftool merge`: all the files (the files of the
directories included) are combined into a single output, in the order described above (`pdftool merge` merges in lexicographic order).
For `pdftool merge` without `-o`, the output is named after the first file with a `_merged` postfix, in the folder of that file:
avoid merging a directory twice, as the previous output would be included.

## `renamer`, `datefixer`, `audiotool fix-mp3-meta` and `audiotool normalize`

These tools used to take their files with `-f` / `--files`. They now take them with `-i` / `--inputfiles` like all the other
tools (`-f` / `--files` is still accepted as a deprecated alias).

- `renamer` and `datefixer` process the image and video files of the directories (recursively), like the other tools.
- `fix-mp3-meta` and `normalize` process the directories **album by album**: each sub-directory of a directory is an album
  whose name gives the artist, album and year used to fix the tags, so the directories are not flattened into a list of files.
  The audio files given explicitly are processed with the context of their parent directory.
