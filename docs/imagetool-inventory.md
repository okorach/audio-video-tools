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

# imagetool inventory

Inventories the photos found in directories and/or disk drives (processed recursively) into a CSV file: one row per photo, with
its full path, short name, size, dimensions, dates, GPS coordinates, device and other common EXIF metadata.

```
imagetool inventory -i <photos, directories and/or disk drives> [-o <output.csv>] [--threads <n>] [-v CRITICAL|ERROR|WARNING|INFO|DEBUG]
```

| Option | Description |
|---|---|
| `-i` | Photos, directories and/or disk drives to inventory (directories are scanned recursively) |
| `-o` | CSV file to write. Default: `photo-inventory.csv` |
| `--threads` | Number of threads reading the photos' metadata in parallel. Default: 8 |
| `-v` | Verbosity, see [verbosity.md](verbosity.md) |

The photos are read in parallel: the list of photos is split into `--threads` chunks, each chunk read by its own thread with a
single `exiftool` process kept open for the whole chunk (spawning one `exiftool` process per photo would be much slower on a large
photo collection, such as a whole disk drive). The progress (count/total and percentage) is logged at most every 10 seconds, eg
`1346/3384 pictures 39.8%`.

The CSV file has one row per photo, with the columns below (in this order). A column is empty when the corresponding metadata is
not present in the photo:

| Column | Description |
|---|---|
| `full_path` | Absolute path of the photo |
| `file_name` | Name of the photo, without its path |
| `size_bytes` | Size of the file, in bytes |
| `width`, `height` | Dimensions of the photo, in pixels |
| `date_taken` | Date and time the photo was taken (EXIF `DateTimeOriginal`, else `CreateDate`) |
| `date_created`, `date_modified` | Creation and modification dates of the file itself |
| `gps_latitude`, `gps_longitude`, `gps_altitude` | GPS coordinates the photo was taken at |
| `device` | Make and model of the camera or phone that took the photo |
| `lens_model`, `iso`, `aperture`, `exposure_time`, `focal_length`, `orientation`, `software` | Other common EXIF metadata |

Requires `exiftool` on PATH.
