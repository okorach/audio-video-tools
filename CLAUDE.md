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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python batch tools for transcoding and manipulating audio, video, image and PDF files, built as a high-level wrapper around FFmpeg. The package name is `audio-video-tools` (importable as `mediatools`, version in `pyproject.toml` and `mediatools/version.py`). It provides both a Python library and CLI tools:

- 4 unified commands, `videotool`, `audiotool`, `imagetool` and `pdftool`, that run the tools as `<command> <action> <parameters>` (registry in `mediatools/tools.py`, list of the actions in `docs/unified-commands.md`)
- 4 standalone commands that are not about a single kind of file: `linker`, `renamer`, `datefixer` and `shuffle`

All are installed as console entry points (`[project.scripts]` of `pyproject.toml`).

## Build and Development Commands

```bash
# Run tests with coverage
coverage run -m pytest --junitxml=build/ut.xml
coverage xml -o build/coverage.xml

# Run a single test file / test
pytest tests/test_video.py
pytest tests/test_video.py::test_name
pytest tests -k "rotate or flip"

# Linting (ruff + pylint + flake8 + bandit), configuration in pyproject.toml and conf/pylintrc
ruff check .
pylint --rcfile conf/pylintrc ./*.py ./*/*.py -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"
flake8 --ignore=W503,E128,C901,W504,E302,E265,E741,W291,W293,W391,F401,E722 --max-line-length=150 .
bandit --exit-zero -f json --skip B311,B303,B101 -r . -x .vscode,./tests

# Format code
black --line-length=150 --target-version py310 .

# Lint, test and scan with SonarQube
./scan.sh

# Build and install locally
./deploy.sh

# Build and publish to PyPI
./deploy.sh pypi
```

The full test suite takes a few minutes: it runs ffmpeg on small generated videos. The tests that need Ghostscript, exiftool or bash are skipped when they are missing, and the Windows only tests are skipped on the other platforms. The tools write their logs in `<tool>.log` files of the current directory (git ignored).

## Architecture

### Class Hierarchy

The core abstraction is a media file hierarchy rooted in `utilities/file.py`:

```
utilities.file.File
  └── mediatools.mediafile.MediaFile     (FFmpeg probe, encoding, specs)
       ├── mediatools.videofile.VideoFile (video codec, fps, resolution)
       ├── mediatools.audiofile.AudioFile (audio tags via mp3_tagger/music_tag)
       └── mediatools.imagefile.ImageFile (EXIF via exifread/pyexiftool, resolution)
```

### Package Layout

- **`mediatools/`** — Core library. Each module typically has a `main()` function that serves as a CLI entry point (run by an action of `mediatools/tools.py`). `utilities.py` holds what the tools share (command line arguments, ffmpeg execution, hardware acceleration, progress), `metacopy.py` the preservation of dates and geotagging.
- **`cli/`** — Two additional CLI frontends (`encode.py`, `shuffle.py`) that wrap `mediatools` functionality.
- **`filters/`** — FFmpeg filter abstraction: `Simple` filters (`-vf`/`-af`) and `Complex` filter graphs (`-filter_complex`). `filter.py` has the objects, `filters.py` the functions returning strings.
- **`utilities/`** — `file.py` provides base `File` class and `FileType` enum (AUDIO_FILE, VIDEO_FILE, IMAGE_FILE) based on extension.
- **`tests/`** — pytest tests, one file per tool or module. Test media files live in `it/`.
- **`docs/`** — One markdown page per feature (a tool, quality, resolution aliases, verbosity, hardware acceleration, input files, metadata preservation...).
- **`batch-files*/`** — Windows batch files (drag and drop of media files) that call the tools.
- **`conf/pylintrc`** — pylint configuration. `ruff2sonar.py` converts the ruff report for SonarQube.

### Configuration System

Encoding presets are defined in Java properties format (`jprops` library):
- **`mediatools/media-tools.properties`** — 50+ encoding profiles (720p, 1080p, 4K, timelapse, etc.) with FFmpeg command templates, and the defaults (`default.video.*`, `default.slideshow.resolution`, `default.slideshow.fps`...)
- **`~/.mediatools.properties`** — User overrides (auto-created from defaults, so a new property is not in it: the code needs a fallback)
- Loaded once at import time via `mediatools/media_config.py`

Profile keys follow the pattern: `<profilename>.cmdline` (FFmpeg args), `<profilename>.extension` (output format). Binary paths: `binaries.ffmpeg`, `binaries.ffprobe`.

### Option Mapping

`mediatools/options.py` defines dual option namespaces:
- `Option` class — mediatools naming (e.g., `vcodec`, `abitrate`, `fps`, `quality`)
- `OptionFfmpeg` class — FFmpeg naming (e.g., `c:v`, `b:a`, `r`, `crf`)
- `M2F_MAPPING` / `F2M_MAPPING` dicts translate between them
- `CODECS` / `HW_ACCEL_CODECS` dicts map friendly names to FFmpeg codec names (e.g., `h265` → `libx265` or `hevc_nvenc`)
- The allowed values of the choices: `QUALITY_LEVELS`, `ROTATION_ANGLES`, `FLIP_DIRECTIONS`

### Unified Commands

`mediatools/tools.py` has one dictionary per command (`VIDEO_ACTIONS`, `AUDIO_ACTIONS`, `IMAGE_ACTIONS`, `PDF_ACTIONS`) that maps an action to `"module:main"` and its description. To add a tool: write the module with its `main()`, register it in the dictionaries of the commands it belongs to, add its page in `docs/`, its row in `docs/unified-commands.md` and a line in the README. A new standalone console script must be added to both `pyproject.toml` (the one that `deploy` builds from) and `setup.py`.

### CLI Pattern

Each CLI tool follows this pattern:
1. `util.get_common_args(name, description)` — creates argparse parser with standard `-i`/`-o`/`-v`/`-s` flags (`--hw_accel`, `--keepName`, `--width`, `--height`, `--aspect`). The tools that don't use it add the options with `util.add_input_args`, `util.add_output_args`, `util.add_verbosity_arg` and `util.add_hw_accel_arg`.
2. Tool-specific arguments are added to the parser. The tools that generate a video use `video.add_quality_arg` / `video.add_reencode_args` (`--vcodec`, `--quality`, `--fps`) or `video.add_video_args`.
3. `util.parse_media_args(parser, input_type=...)` — parses args, resolves resolution, detects hardware acceleration, and expands the directories given to `-i` into the (recursive) list of files of the `input_type` FileType(s)
4. Core logic runs via the media file classes or utility functions, once per input file with `util.process_input_files(kwargs, process)` (tools combining all the files, like concat, use `kwargs[util.INPUT_FILES]` as a whole)
5. `util.generated_file(path)` — logs output file path

Notes:
- The names of the input and output options are `util.INPUT_FILES` and `util.OUTPUT_FILE`: use the constants, not the literals.
- The verbosity is `-v CRITICAL|ERROR|WARNING|INFO|DEBUG` (`INFO` by default). `-g <0-4>` is a hidden deprecated alias.
- `--resolution` accepts `WxH` or an alias (`4k`, `2.7k`, `2.5k`, `fhd`, `hd`, `2160p`, `1080p`, `720p`...): the alias is converted when the arguments are parsed (`resolution.canonical`), because ffmpeg gives a different meaning to some of them.

### Hardware Acceleration

The `--hw_accel auto|on|off` option is in the common arguments. Functions that run hardware accelerated ffmpeg commands decide with `util.use_hardware_accel(**kwargs)` and are decorated with `@util.hw_accel_fallback`, which runs them again on the CPU if a command fails in auto mode. Some filters only exist on the CPU (rotate, flip, the effects of the slideshow): the video is then decoded and filtered on the CPU and only encoded by the GPU (`mediafile.use_gpu_filters`).

### Video Quality

`--quality high|medium|low` sets the constant quality of the video encoding (`-crf`, or `-cq` for the nvenc encoders): x264 18/23/28, x265 23/28/33 (`mediafile.get_quality_settings`). It is `high` by default, unless a video bitrate is given (option or profile) without a quality: the bitrate is then used.

### Dates of the Generated Files

A file generated from a source file gets its creation and modification dates and its geotagging. `util.run_ffmpeg` does it for every ffmpeg command (`metacopy.copy_after_ffmpeg`); the code that generates files without ffmpeg calls `metacopy.copy_date_and_geotag`; the code that modifies a file in place uses `metacopy.preserve_dates` or `@metacopy.keeps_dates`.

### Progress

`util.GlobalProgress` logs the global progress and ETA of the tools that process several files (steps can have different weights, like the clips and the assembly of a slideshow). The ffmpeg progress lines (every 2 seconds) end with the progress and ETA of the file and the global ones.

### External Dependencies

Requires `ffmpeg` and `ffprobe` on PATH (or configured via properties). Image metadata operations and the preservation of dates require `exiftool`. The PDF tools require Ghostscript. The hardware acceleration requires an Nvidia GPU.

## Testing

- pytest, one test file per tool or module. `tests/conftest.py` generates small videos and audio once per session (`short_video`, `video_5s`, `short_audio`); `it/` has the other media files.
- Mock the execution of ffmpeg (`util.run_ffmpeg`, `util.run_os_cmd`) to test the commands that are built; run it for real on the small media to test the result.
- Use `monkeypatch` for the temporary modifications, `pytest.raises` for the exceptions (with one call in the block), `pytest.fail("message")` and not `assert False`, no `assert True`.
- Some tests check the conventions of the repository: `test_copyright.py` (license header in all the files), `test_batch_files.py` (conventions of the batch files), `test_ci_version.py` (the version of the project is the same everywhere).

## Documentation

Each feature has a page in `docs/` (options, behavior, examples), linked from the README. Keep the page and the `--help` of a tool in sync with its options.

## Batch Files

- The tools process all the files they are given: a batch file calls the tool once with `-i %*`, it doesn't loop on the files.
- No `pause` at the end of a batch file.
- The parameters are asked with `set /p` after a default (`setlocal enabledelayedexpansion`, then `!variable!`): quality (default `high`) for the encodings, resolution, angle...
- Each batch file has the license header (`::` comments).

## CI and Release

- GitHub Actions (`.github/workflows/build.yml`): tests with coverage, ruff, pylint, flake8, bandit, then SonarCloud. The version of the project is read in `pyproject.toml` and passed to the scanner (`-Dsonar.projectVersion`). The `Jenkinsfile` does the same for SonarQube.
- To bump the version, change `pyproject.toml` and `mediatools/version.py` (both are checked by a test).
- Changes go through a branch and a pull request on `main`; the PR must pass the tests and the SonarCloud quality gate.

## Code Style

- **Line length:** 150 (black/flake8/pylint)
- **Formatter:** `black --line-length=150`
- All files that can hold comments carry the LGPL v3 license header (`#`, `::`, `//`, or an HTML comment for markdown); a test checks it
- Python 3.10+ required
- All functions, methods, classes and modules have a docstring (third person, eg "Returns...") and type hints for all their parameters and their return value (`**kwargs: object`)
- All new code should be systematically covered by tests
- All new code should not have any issues reported by ruff (`select = ["ALL"]` with the ignores of `pyproject.toml`), pylint or SonarQube
