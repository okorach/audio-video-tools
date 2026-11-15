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
its full path, short name, size, dimensions, a perceptual fingerprint, dates, GPS coordinates, device, other common EXIF
metadata and a duplicate likelihood (see below) to help detect duplicates and near-duplicates.

GIF files are never inventoried (not photos: animations, screenshots...), whether found under a scanned directory or given
directly in `-i`.

```
imagetool inventory -i <photos, directories, disk drives, or a single existing inventory CSV> [-o <output.csv>] [--threads <n>] [--dedup] [-v CRITICAL|ERROR|WARNING|INFO|DEBUG]
```

| Option | Description |
|---|---|
| `-i` | Photos, directories and/or disk drives to inventory (directories are scanned recursively), or a single existing inventory CSV file (see below) |
| `-o` | CSV file to write. Default: `photo-inventory.csv`, or the input CSV file itself when `-i` is one |
| `--threads` | Number of threads reading the photos' metadata in parallel. Default: 8 |
| `--dedup` | Interactively review the likely duplicates of an existing inventory CSV given in `-i`, and delete one of each pair, see below |
| `-v` | Verbosity, see [verbosity.md](verbosity.md) |

Finding all the photos under a directory or a disk drive can itself take a while before the inventory can start: the number of
photos found so far is logged at most every 10 seconds, eg `Collected 1346 images for inventory`, and once more when the
collection is complete, eg `3384 images collected, now processing...`.

The photos are then read in parallel: the list of photos is split into `--threads` chunks, each chunk read by its own thread with
a single `exiftool` process kept open for the whole chunk (spawning one `exiftool` process per photo would be much slower on a
large photo collection, such as a whole disk drive). The processing progress and its ETA (estimated from the average time per
photo processed so far, applied to the remaining photos) are logged at most every 30 seconds, eg
`Processed 1346/3384 images - ETA 00:12:34.567`.

The CSV file has one row per photo, with the columns below (in this order). A column is empty when the corresponding metadata is
not present in the photo:

| Column | Description |
|---|---|
| `full_path` | Absolute path of the photo |
| `file_name` | Name of the photo, without its path |
| `size_bytes` | Size of the file, in bytes |
| `width`, `height` | Dimensions of the photo, in pixels |
| `fingerprint` | Perceptual fingerprint of the photo, see below |
| `date_taken` | Date and time the photo was taken (EXIF `DateTimeOriginal`, else `CreateDate`) |
| `date_created`, `date_modified` | Creation and modification dates of the file itself |
| `gps_latitude`, `gps_longitude`, `gps_altitude` | GPS coordinates the photo was taken at |
| `device` | Make and model of the camera or phone that took the photo |
| `lens_model`, `iso`, `aperture`, `exposure_time`, `focal_length`, `orientation`, `software` | Other common EXIF metadata |
| `duplicate_likelihood` | Likelihood (0-100) that this photo is a duplicate of another one of the inventory, see below |
| `duplicate_of` | Full path of the most likely duplicate (empty if `duplicate_likelihood` is empty) |

## Fingerprint

`fingerprint` is a perceptual fingerprint of the photo, a 64 character hex string (256 bits), computed only from its pixels
(after applying its EXIF orientation), not from its file name or its metadata. It is meant to later detect duplicate or
near-duplicate photos across the inventory:

- Two photos with the exact same pixels get the exact same fingerprint, whatever their file name, dates or metadata.
- The same photo resized, or cropped a bit, gets a fingerprint close to the original one (a small number of bits differ),
  while an unrelated photo gets a fingerprint far from it (many bits differ).
- `image_inventory.hamming_distance(fingerprint_1, fingerprint_2)` returns the number of bits that differ between two
  fingerprints (0 for identical photos), which can be turned into a match probability between two photos.

The fingerprint of a photo that can't be read as an image (corrupted file, unsupported format) is empty. A very large photo
(more pixels than Pillow's decompression bomb safety limit) logs a warning naming the file, since Pillow's own warning about
it doesn't.

## Duplicate detection

`duplicate_likelihood` (0-100) and `duplicate_of` estimate how likely a photo is a duplicate, or a near-duplicate, of another
photo of the inventory, and point to that most likely duplicate. They are computed as the last phase of the inventory, by
comparing each photo to the others on:

- How close their fingerprints are (`hamming_distance()`, the main criterion).
- Whether their file size, dimensions, date taken, device and GPS coordinates match.

Only the criteria present on both photos being compared count, so missing metadata never lowers the likelihood: a photo with
little or no EXIF metadata can still be matched on its fingerprint alone. `duplicate_likelihood` and `duplicate_of` are empty
when a photo has too little in common with any other one to say anything meaningful, or none at all.

To keep this phase fast on a large inventory, photos are only compared to the others sharing an exact file size, an exact
date taken, or the leading bits of their fingerprint: comparing every photo to every other one would not scale to a disk
drive's worth of photos. As a result, a duplicate with none of these in common with the original (eg a heavily re-edited copy,
saved on a different date, with its metadata stripped) may be missed.

`duplicate_likelihood` and `duplicate_of` can also be (re)computed on their own, from an existing inventory CSV, without
rescanning any photo: pass that CSV file as the single `-i` of a new `imagetool inventory` run. Without `-o`, the CSV is
amended in place.

```
imagetool inventory -i photo-inventory.csv
```

## Deduplication

`imagetool inventory -i photo-inventory.csv --dedup` interactively reviews the pairs of photos likely to be duplicates
of an existing inventory CSV (one that already has its `duplicate_likelihood` and `duplicate_of` columns computed),
from the highest likelihood down to the lowest, and lets you delete one of each pair.

For each pair, it prints their size, date taken, device and GPS coordinates (rounded to 4 decimal digits), and a
recommendation of which one to delete, decided by the first of these rules that applies:

1. One is significantly smaller than the other (less than 80% of its size): the smaller one is recommended.
2. One still has its camera/phone original file name (eg `IMG_1234.jpg`, `PXL_20210101_123456.jpg`, `DSC_0001.jpg`)
   while the other was renamed to something more descriptive: the one with the original name is recommended.
3. One has GPS coordinates and the other has not: the one without GPS coordinates is recommended.

If none of these rules applies, no recommendation is made: this is expected for 2 byte-for-byte copies with the same
original name, size and GPS coordinates (eg the same phone photo backed up to 2 folders), since nothing distinguishes
one from the other. For each pair, answer `1` or `2` to delete that photo, `0` to keep both, or just press `Enter` to
go with the recommendation (nothing happens on `Enter` when there is none).

A photo chosen for deletion is removed from disk and from the CSV, which is rewritten after each removal so an
interrupted review can be resumed later without going through the pairs already handled. A photo already missing on
disk (eg deleted by some other means since the inventory was made) is removed from the CSV too; one that still exists
but could not be deleted (eg permission denied) is kept in the CSV.

Requires `exiftool` on PATH.
