# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python batch tools for transcoding and manipulating audio, video, and image files, built as a high-level wrapper around FFmpeg. The package name is `audio-video-tools` (importable as `mediatools`). It provides both a Python library and 28 CLI tools installed as console entry points.

## Build and Development Commands

```bash
# Run tests with coverage
./run_tests.sh
# Or directly:
coverage run -m pytest --junitxml=build/ut.xml
coverage xml -o build/coverage.xml

# Run a single test
pytest tests/test_video.py
pytest tests/test_video.py::TestClassName::test_method_name

# Linting (pylint + flake8 + bandit)
./run_linters.sh

# Individual linters
pylint *.py */*.py -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"
flake8 --ignore=W503,E128,C901,W504,E302,E265,E741,W291,W293,W391,F401,E722 --max-line-length=150 .
bandit --exit-zero -f json --skip B311,B303,B101 -r . -x .vscode,./tests

# Format code
black --line-length=150 .

# Build and install locally
./deploy.sh

# Build and publish to PyPI
./deploy.sh pypi
```

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

- **`mediatools/`** — Core library. Each module typically has a `main()` function that serves as a CLI entry point (registered in `setup.py` `entry_points`).
- **`cli/`** — Two additional CLI frontends (`encode.py`, `shuffle.py`) that wrap `mediatools` functionality.
- **`filters/`** — FFmpeg filter abstraction: `Simple` filters (`-vf`/`-af`) and `Complex` filter graphs (`-filter_complex`).
- **`utilities/`** — `file.py` provides base `File` class and `FileType` enum (AUDIO_FILE, VIDEO_FILE, IMAGE_FILE) based on extension.
- **`tests/`** — pytest tests. Test media files live in `it/`.

### Configuration System

Encoding presets are defined in Java properties format (`jprops` library):
- **`mediatools/media-tools.properties`** — 50+ encoding profiles (720p, 1080p, 4K, timelapse, etc.) with FFmpeg command templates
- **`~/.mediatools.properties`** — User overrides (auto-created from defaults)
- Loaded once at import time via `mediatools/media_config.py`

Profile keys follow the pattern: `<profilename>.cmdline` (FFmpeg args), `<profilename>.extension` (output format). Binary paths: `binaries.ffmpeg`, `binaries.ffprobe`.

### Option Mapping

`mediatools/options.py` defines dual option namespaces:
- `Option` class — mediatools naming (e.g., `vcodec`, `abitrate`, `fps`)
- `OptionFfmpeg` class — FFmpeg naming (e.g., `c:v`, `b:a`, `r`)
- `M2F_MAPPING` / `F2M_MAPPING` dicts translate between them
- `CODECS` / `HW_ACCEL_CODECS` dicts map friendly names to FFmpeg codec names (e.g., `h265` → `libx265` or `hevc_nvenc`)

### CLI Pattern

Each CLI tool follows this pattern:
1. `util.get_common_args(name, description)` — creates argparse parser with standard `-i`/`-o`/`-g`/`-s` flags
2. Tool-specific arguments are added to the parser
3. `util.parse_media_args(parser)` — parses args, resolves resolution, detects hardware acceleration
4. Core logic runs via the media file classes or utility functions
5. `util.generated_file(path)` — logs output file path

### External Dependencies

Requires `ffmpeg` and `ffprobe` on PATH (or configured via properties). Image metadata operations require `exiftool`.

## Code Style

- **Line length:** 150 (black/flake8), 128 (pylint)
- **Formatter:** `black --line-length=150`
- All Python files carry the LGPL v3 license header
- Python 3.6+ required
