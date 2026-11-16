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

# `audiotool volume` / `videotool volume`

Changes the volume of one or more audio or video files, either to a value you give (`--volume`) or, across a batch of files, to a level normalized on their average (`--normalize`).

## Single file / fixed change

```bash
audiotool volume -i song.mp3 --volume 400%     # 4x louder (relative change)
audiotool volume -i song.mp3 --volume 6dB       # +6dB (absolute change)
audiotool volume -i song.mp3 --volume -3dB      # -3dB
```

The result is written to `<file>.volume.<ext>` unless `-o` is given.

## Normalizing the volume across many files

```bash
audiotool volume -i E:\Musique --normalize
audiotool volume -i E:\Musique --normalize --threshold 1.5 -o report.csv
```

`--normalize` measures the mean volume (FFmpeg's `volumedetect` filter) of every input file, computes their average, and leaves files whose mean volume is within `--threshold` dB of that average unchanged (`2.0` dB by default). The other files are adjusted to reach the average:

- The corrected file keeps the original name and path.
- The untouched original is kept alongside it as `<file>.before_volume.<ext>`.
- Every adjusted file is reported, with its full path, in a CSV report (`-o`, `volume-normalize.csv` in the current directory by default), with columns `full_path`, `mean_volume_db`, `target_volume_db`, `applied_gain_db`, `backup_file`.

`--volume` and `--normalize` are mutually exclusive.
