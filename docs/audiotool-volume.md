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
- The untouched original is kept alongside it as `<file>.before_volume.<ext>` (`<file>.before_volume.2.<ext>`... if the file already has a backup: no backup is ever overwritten, see [restore.md](restore.md)). Backups are ignored by the next normalizations.
- Only the audio is re-encoded, in its own codec and at its own bitrate (same sample format for FLAC and ALAC): the video, cover art, subtitles and tags are copied. A file whose codec or bitrate can't be kept is not modified.
- A file that can't be measured or adjusted is logged and skipped, the others are still processed, and the command exits with code 1.
- Every adjusted file is reported, with its full path, in a CSV report: `-o`, or `volume-normalize.csv` (`volume-normalize.2.csv`...) in the first input directory (or the directory of the first input file). Its columns are `full_path`, `mean_volume_db`, `target_volume_db`, `applied_gain_db`, `backup_file`.

A large gain applied to a quiet file whose peaks are already high can clip it: check such files, the original is in the backup.

`--audio_only` ignores the video files, eg in a directory holding both music and videos (the "audio normalize.bat" batch file uses it).

## Undoing a normalization

```bash
audiotool volume -i E:\Musique --restore
```

`--restore` puts the files back as they were before `--normalize`: each modified file is removed and replaced by its original, renamed from its backup (content and dates unchanged). It looks for the backups in the input directories (recursively), or next to the input files.

- After several normalizations, one `--restore` undoes them all, in reverse order: `<file>.before_volume.<n>.<ext>` is restored first, then `<n-1>`, down to `<file>.before_volume.<ext>`.
- The `volume-normalize.csv` reports found there are removed once none of their backups remains. Give `-o` to also remove a report written elsewhere.
- A file modified by another tool after its normalization needs that tool to be restored first, see [restore.md](restore.md).
- Any change made to a file after its normalization (eg its tags) is lost with the modified file.
- A file that can't be restored is logged and keeps its older backups (run `--restore` again once fixed), the others are still restored, the reports are kept and the command exits with code 1.
- The log file of the tool (`media-volume.log`, in the current directory) is not removed.

`--volume`, `--normalize` and `--restore` are mutually exclusive.
