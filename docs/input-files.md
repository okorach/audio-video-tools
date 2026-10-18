# Input files and directories (`-i`)

The `-i` / `--inputfiles` option of the tools takes a **list of files and/or directories**.
Each directory is replaced by all the files it contains, **recursively**.

```
# file1.mp4, file2.mp4 and all the video files in dir1 (and its sub-directories) are processed
media-volume -i file1.mp4 file2.mp4 dir1 --volume 200%
```

## Rules

- The arguments are processed in the order given. The files of a directory are in alphabetical order of their paths
  (case insensitive), sub-directories included: `dir1/b.mp4`, `dir1/sub/d.mp4`, `dir1/z.mp4`.
- A file given explicitly is always taken, whatever its type. The tool reports an error if it can't process it.
- In a directory, only the files that the tool can process are taken: video files for the video tools (`media-crop`,
  `video-reverse`, `video-speed`...), image files for the image tools (`image-scale`, `image-blinds`...), audio files for
  the audio tools (`audio-speed`...), audio and video files for tools that handle both (`audio-denoise`, `media-volume`,
  `media-cut`, `video-encode`), PDF files for the PDF tools. Tools that handle any kind of media take all the audio,
  video and image files.
- A directory without any matching file is an error (exit code 1).

## Tools processing each file

`media-crop`, `media-cut`, `media-volume`, `media-specs`, `video-reverse`, `video-speed`, `video-metadata`, `video-deshake`,
`video-stabilize`, `video-enhance`, `video-encode`, `encode`, `encodeauto`, `image-scale`, `image-blinds`, `image-shake`,
`image-to-video`, `audio-speed`, `audio-split`, `audio-denoise`, `pdf-split`, `pdf-compress`:
each file is processed independently, and the output file name is derived from the input file name.

- `-o` can't be used when there are several input files (exit code 2).
- A failure on one file doesn't prevent the next ones from being processed, the exit code is 1 at the end.

## Tools combining the files

`video-concat`, `audio-concat`, `video-mux`, `image-stack`, `image-poster`, `pdf-merge`: all the files (the files of the
directories included) are combined into a single output, in the order described above (`pdf-merge` merges in lexicographic order).
For `pdf-merge` without `-o`, the output is named after the first file with a `_merged` postfix, in the folder of that file:
avoid merging a directory twice, as the previous output would be included.

## `renamer`, `datefixer`, `fix-mp3-meta` and `audio-normalize`

These tools used to take their files with `-f` / `--files`. They now take them with `-i` / `--inputfiles` like all the other
tools (`-f` / `--files` is still accepted as a deprecated alias).

- `renamer` and `datefixer` process the image and video files of the directories (recursively), like the other tools.
- `fix-mp3-meta` and `audio-normalize` process the directories **album by album**: each sub-directory of a directory is an album
  whose name gives the artist, album and year used to fix the tags, so the directories are not flattened into a list of files.
  The audio files given explicitly are processed with the context of their parent directory.
