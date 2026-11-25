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

Inventories the photos found in directories and/or disk drives (processed recursively), or picked from a Google Photos
library (`--google`), into a CSV file: one row per photo, with its full path, short name, size, dimensions, a perceptual
fingerprint, dates, GPS coordinates, device, other common EXIF metadata and a duplicate likelihood (see below) to help
detect duplicates and near-duplicates.

GIF files are never inventoried (not photos: animations, screenshots...), whether found under a scanned directory or given
directly in `-i`. The Windows recycle bin (`$RECYCLE.BIN`) is never walked into when scanning a directory or disk drive.

```
imagetool inventory -i <photos, directories, disk drives, or a single existing inventory CSV> [-o <output.csv>] [--threads <n>] [--dedup] [-v CRITICAL|ERROR|WARNING|INFO|DEBUG]
imagetool inventory --google [-o <output.csv>] [--threads <n>]
```

| Option | Description |
|---|---|
| `-i` | Photos, directories and/or disk drives to inventory (directories are scanned recursively), or a single existing inventory CSV file (see below). Not used with `--google` |
| `-o` | CSV file to write. Default: `photo-inventory.csv`, or the input CSV file itself when `-i` is one, or `<Pictures>/google-photos-inventory.csv` with `--google` |
| `--threads` | Number of threads reading the photos' metadata (or, with `--google`, downloading them) in parallel. Default: 8 |
| `--dedup` | Interactively review the likely duplicates of an existing inventory CSV given in `-i`, and delete one of each pair, see below |
| `--google` | Inventory photos picked from a Google Photos library instead of local files, see below |
| `-v` | Verbosity, see [verbosity.md](verbosity.md) |

Finding all the photos under a directory or a disk drive can itself take a while before the inventory can start: the number of
photos found so far is logged at most every 10 seconds, eg `Collected 1346 images for inventory`, and once more when the
collection is complete, eg `3384 images collected, now processing...`.

The photos are then read in parallel: the list of photos is split into `--threads` chunks, each chunk read by its own thread with
a single `exiftool` process kept open for the whole chunk (spawning one `exiftool` process per photo would be much slower on a
large photo collection, such as a whole disk drive). The processing progress and its ETA (estimated from the average time per
photo processed so far, applied to the remaining photos) are logged at most every 30 seconds, eg
`Processed 1346/3384 images - ETA 00:12:34.567`.

If the output CSV already exists (eg from a previous run over the same directory or drive), a photo already in it that has
not been modified since (its own modification date is not after the CSV file's) reuses its fingerprint and metadata from
there instead of being read again: only the new or modified photos are actually processed, which makes re-inventorying a
large, mostly unchanged collection much faster.

The CSV file has one row per photo, with the columns below (in this order). A column is empty when the corresponding metadata is
not present in the photo:

| Column | Description |
|---|---|
| `full_path` | Absolute path of the photo |
| `file_name` | Name of the photo, without its path |
| `size_bytes` | Size of the file, in bytes |
| `width`, `height` | Dimensions of the photo, in pixels |
| `fingerprint` | Perceptual fingerprint of the photo, see below |
| `date_taken` | Date and time the photo was taken (EXIF `DateTimeOriginal`, else `CreateDate`), falling back to the date guessed from the file name (eg `IMG_20180706_125922.jpg`), then to the file's own creation/modification date, when there is no EXIF date |
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
- Whether their dimensions, date taken, device and GPS coordinates match.
- How close their file sizes are: a full score for identical sizes, 66% of it when they differ by less than 5%, 33% when they
  differ by less than 10% (relative to the largest file), nothing otherwise.

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

## Google Photos

`imagetool inventory --google` inventories photos picked from a Google Photos library instead of local files, using
the Google Photos [Picker API](https://developers.google.com/photos/picker/guides/get-started). Google restricts its
older Library API, since 2025, to the media a third-party app itself uploaded, so listing an existing library needs
the Picker API instead: each run opens a page in your browser where you select the photos and/or albums to inventory
(selecting whole albums, or your whole library, is possible in a single pick), then click Done.

One-time setup, in the [Google Cloud console](https://console.cloud.google.com/):

1. Create a project (or reuse one), enable the **Google Photos Picker API** for it.
2. Create an OAuth 2.0 client ID of type **Desktop app**, and download its credentials JSON file.
3. Save that file as `~/.mediatools-google-credentials.json`, or point the `google.credentials_file` property of
   `~/.mediatools.properties` to wherever you saved it.

The first run opens a browser for you to sign in and consent; the resulting token is cached (`google.token_file`
property, default `~/.mediatools-google-token.json`) so later runs don't ask again, until the token is revoked.

The columns the Picker API does not expose for a picked photo are left empty: GPS coordinates, the file's own
creation/modification dates (as opposed to the date it was taken), lens model, orientation and software. `date_taken`
is the photo's `createTime`, falling back to the date guessed from its file name, then to the `Last-Modified` HTTP
header of the original file, when `createTime` is missing. The duplicate likelihood (see above) is computed across
the picked photos only, not against any local inventory.

Without `-o`, the CSV is written to `google-photos-inventory.csv` in the OS pictures folder (`%USERPROFILE%\Pictures`
on Windows) rather than the current directory, since there is no input directory to default it from. `--dedup` works
on a Google Photos inventory CSV like any other, but since a Google Photos row has no local file, the photo recommended
for deletion is only ever removed from the CSV, never from your Google Photos library.

The Google Photos picker limits a single selection to a few thousand items, so inventorying a large library takes
several runs. Running `--google` again with the same `-o` (or its default) is cumulative: the existing CSV is
extended, not replaced, a picked photo already in it is skipped (neither re-downloaded nor added again), and the
duplicate likelihood is recomputed across the whole, now larger, CSV.

## Deduplication

`imagetool inventory -i photo-inventory.csv --dedup` interactively reviews the pairs of photos likely to be duplicates
of an existing inventory CSV (one that already has its `duplicate_likelihood` and `duplicate_of` columns computed),
from the highest likelihood down to the lowest, and lets you delete one of each pair.

For each pair, it prints their size, date taken, device and GPS coordinates (rounded to 4 decimal digits), and a
recommendation of which one to delete, decided by the first of these rules that applies:

1. One, and not the other, matches one of the `dedup.delete_priority` property's regexes (see below), checked in
   the order they are listed there: that one is recommended. By default, in order:
   1. A `.picasaoriginals` folder (Picasa's hidden backup of a photo's pixels before any edit done in the app,
      anywhere in its full path).
   2. A tilde (`~`) anywhere in its full path, as commonly found in a backup or temporary copy's name (eg
      `~lockfile`, `image~.jpg`).
   3. A "copy"/"copie" suffix on its file name, as commonly added when a file manager duplicates a file (eg
      `some-picture copie.jpg`, `some-picture - Copy.jpg`, `some-picture copy (2).jpg`).
   4. A folder whose name contains "duplicate" (anywhere in its full path, eg `Duplicates`, `Duplicate Photos`),
      the strongest folder signal since it was deliberately filed away as one.
   5. An `a_trier`/`a trier` folder (French for "to be sorted"; matched case, accent and underscore/space
      insensitively, anywhere in its full path), as still awaiting review.
   6. An unedited camera/phone original file name (eg `IMG_1234.jpg`, `PXL_20210101_123456.jpg`,
      `PANO_20190415_103823.jpg`, `DSC_0001.jpg`, `HPIM1234.jpg`, `20130804_174038.jpg`,
      `25-12-2011 16-46-10_0021.JPG`, `2014-07-20 20.19.20.jpg`), as opposed to a descriptive name the other was
      renamed to.
2. Both are in the exact same folder and their file names only differ by a trailing sequence number (eg
   `Vallandry 2016 081.jpg` and `Vallandry 2016 140.jpg`): the same shot exported/copied twice under the same
   batch-numbering scheme, so the one with the highest number (the later copy) is recommended. This one isn't a
   pattern match (it compares the 2 photos' numbers to each other), so it isn't configurable like rule 1.
3. One is significantly smaller than the other (less than 80% of its size): the smaller one is recommended. Not
   configurable either.
4. One has GPS coordinates and the other has not: the one without GPS coordinates is recommended. Not configurable.

`dedup.delete_priority`, in `~/.mediatools.properties`, is a semicolon-separated list of regexes, matched
case-insensitively against a candidate duplicate's full path, in the order they are listed (whitespace around each
one, eg after a `;`, is stripped and has no effect). Overriding it replaces the whole default list above (rule 1)
entirely; it doesn't add to it. A property created before it existed falls back to that same default. This is how
to extend or reorder any of these pattern checks (eg adding your own camera's file name pattern) without touching
the code; the sequence-number, size and GPS rules (2-4) stay fixed since they compare the 2 photos to each other
rather than matching a pattern.

If none of these rules applies, no recommendation is made: this is expected for 2 byte-for-byte copies with the same
original name, size and GPS coordinates (eg the same phone photo backed up to 2 folders), since nothing distinguishes
one from the other. For each pair, answer `1` or `2` to delete that photo, `0` to keep both, just press `Enter` to go
with the recommendation (nothing happens on `Enter` when there is none), or `q` to stop the review right away (a
letter, not a digit, so it can't be hit by mistake instead of `1`/`2`/`0`): every pair not yet handled, including the
current one, stays in the CSV, so the review can be resumed later from where it was left off.

A pair at 100% duplicate likelihood with a recommendation is deleted automatically, without asking: there is no
reasonable doubt they are the same photo. Every other pair, including a 100% one with no recommendation (eg 2 exact
copies with the same original name), is still asked about.

The 100% threshold is configurable with the `dedup.auto_delete_threshold` property of `~/.mediatools.properties`
(1 to 100, `100` by default, also when the property is missing or invalid). For instance `dedup.auto_delete_threshold = 95`
also deletes, without asking, the recommended photo of every pair that is 95% to 99% alike. Take care: below 100% the
2 photos are similar but not necessarily the same (eg a crop, an edit or a burst shot), and the recommendation then only
relies on the rules above. The pairs below the threshold, or without recommendation, are still asked about.

Before any recommendation or question, each pair is first checked for photos that no longer exist on disk (eg deleted
or moved by some other means since the inventory was made): if one of the two is missing, it is silently removed from
the CSV, the other one is kept, and nothing is asked; if both are missing, both are removed from the CSV, also without
asking, since there is nothing left to choose between.

A photo chosen for deletion is removed from disk and from the CSV, which is rewritten after each removal so an
interrupted review can be resumed later without going through the pairs already handled. One that exists but could
not be deleted (eg permission denied) is kept in the CSV.

Requires `exiftool` on PATH, or, with `--google`, a Google Cloud OAuth2 client (see above).
