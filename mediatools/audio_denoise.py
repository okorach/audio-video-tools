#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

"""Reduces the noise of the audio of audio and video files, with a focus on wind noise.

Wind noise is mostly made of low frequency rumble (below a few hundred Hz) and of broadband gusts. The default
method (wind) removes the rumble with a high-pass filter and attenuates the gusts with an adaptive FFT denoiser
that tracks the noise level. Other methods:
- afftdn: FFT based denoiser only, for steady noises (fan, hiss...)
- arnndn: recurrent neural network denoiser, better on speech. Requires a model file (--model), eg std.rnnn
  from https://github.com/GregorR/rnnoise-models

For video files, the video stream is copied unchanged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mediatools import creator
import mediatools.utilities as util
import utilities.file as fil
from mediatools import log

METHODS = ("wind", "afftdn", "arnndn")
DEFAULT_METHOD = "wind"
# Postfix of the original file name when --keepName is used
BACKUP_POSTFIX = ".before-denoise"
# Wind reduction levels: (high-pass cutoff in Hz, noise reduction in dB)
LEVELS: dict[str, tuple[float, float]] = {"light": (80.0, 6.0), "medium": (120.0, 12.0), "strong": (200.0, 20.0)}
DEFAULT_LEVEL = "medium"
DEFAULT_REDUCTION = 12.0
DEFAULT_NOISE_FLOOR = -50.0
DEFAULT_MIX = 0.8
# Limits of the afftdn nr (noise reduction, dB) and nf (noise floor, dB) options
REDUCTION_RANGE = (0.01, 97.0)
NOISE_FLOOR_RANGE = (-80.0, -20.0)
CUTOFF_RANGE = (20.0, 1000.0)
MIX_RANGE = (-1.0, 1.0)


def _filter_path(path: str) -> str:
    """Escapes a file path to be used as a filter option value (forward slashes, escaped drive colon)"""
    return os.path.abspath(path).replace("\\", "/").replace(":", r"\:")


def _check_range(name: str, value: float, limits: tuple[float, float], unit: str = "") -> None:
    if not limits[0] <= value <= limits[1]:
        raise ValueError(f"--{name} must be between {limits[0]:g} and {limits[1]:g}{unit}, got {value:g}")


def build_filter(
    method: str = DEFAULT_METHOD,
    level: str = DEFAULT_LEVEL,
    cutoff: float | None = None,
    reduction: float | None = None,
    noise_floor: float = DEFAULT_NOISE_FLOOR,
    model: str | None = None,
    mix: float = DEFAULT_MIX,
) -> str:
    """Returns the ffmpeg audio filter. Raises ValueError for invalid parameters.
    - wind: high-pass at cutoff Hz then adaptive afftdn with reduction dB. Cutoff and reduction default to the level preset
    - afftdn: afftdn with reduction dB (default 12) and noise_floor dB
    - arnndn: RNN denoiser with the model file, mix of denoised signal"""
    if method in ("wind", "afftdn"):
        if level not in LEVELS:
            raise ValueError(f"Unknown level {level}, expected one of {', '.join(LEVELS)}")
        if reduction is None:
            reduction = LEVELS[level][1] if method == "wind" else DEFAULT_REDUCTION
        _check_range("reduction", reduction, REDUCTION_RANGE, " dB")
        _check_range("noise-floor", noise_floor, NOISE_FLOOR_RANGE, " dB")
        if method == "afftdn":
            return f"afftdn=nr={reduction:g}:nf={noise_floor:g}"
        if cutoff is None:
            cutoff = LEVELS[level][0]
        _check_range("cutoff", cutoff, CUTOFF_RANGE, " Hz")
        # 2 poles high-pass removes the rumble, afftdn with noise tracking (tn=1) follows the gusts
        return f"highpass=f={cutoff:g}:poles=2,afftdn=nr={reduction:g}:nf={noise_floor:g}:tn=1"
    if method == "arnndn":
        if not model:
            raise ValueError("--model is required with the arnndn method")
        if not os.path.isfile(model):
            raise ValueError(f"Model file {model} not found")
        _check_range("mix", mix, MIX_RANGE)
        return f"arnndn=m='{_filter_path(model)}':mix={mix:g}"
    raise ValueError(f"Unknown method {method}, expected one of {', '.join(METHODS)}")


def backup_file(input_file: str) -> str:
    """Returns the name under which the original file is kept with --keepName: foo.mp4 -> foo.before-denoise.mp4"""
    root, ext = os.path.splitext(input_file)
    return f"{root}{BACKUP_POSTFIX}{ext}"


def denoise(input_file: str, output_file: str | None = None, keep_name: bool = False, **kwargs) -> str:
    """Reduces the noise of the audio of a file. Returns the output file name.
    With keep_name the output file takes the name of the input file, which is renamed with a .before-denoise postfix.
    Options: method, level, cutoff, reduction, noise_floor, model, mix (see build_filter())"""
    if not (fil.is_audio_file(input_file) or fil.is_video_file(input_file)):
        raise ValueError(f"{input_file} is not an audio or video file")
    if keep_name and output_file:
        raise ValueError("An output file can't be given with --keepName")
    if keep_name and os.path.exists(backup_file(input_file)):
        raise ValueError(f"{backup_file(input_file)} already exists, not overwriting it")
    audio_filter = build_filter(**kwargs)
    media = creator.file(input_file)
    media.get_specs()
    bitrate = getattr(media, "abitrate", None) or getattr(media, "audio_bitrate", None)
    output_file = util.automatic_output_file_name(output_file, input_file, "denoised")
    options = [f'-af "{audio_filter}"']
    if fil.is_video_file(input_file):
        options.append("-c:v copy")
    if bitrate:
        options.append(f'-b:a "{bitrate}"')
    log.logger.info("Reducing noise of %s with %s", input_file, audio_filter)
    util.run_ffmpeg(f'-i "{input_file}" {" ".join(options)} "{output_file}"', getattr(media, "duration", None))
    if keep_name:
        # Only once the denoised file is generated: the original is kept under the backup name, the denoised file takes its name
        backup = backup_file(input_file)
        Path(input_file).replace(backup)
        Path(output_file).replace(input_file)
        log.logger.info("Original file kept as %s", backup)
        return input_file
    return output_file


def main() -> None:
    """Entry point of the audio-denoise command"""
    parser = util.get_common_args("audio-denoise", "Reduces the noise (focus on wind noise) of the audio of audio and video files")
    parser.add_argument("--method", required=False, choices=METHODS, default=DEFAULT_METHOD, help="Denoising method (default wind)")
    parser.add_argument(
        "--level", required=False, choices=tuple(LEVELS), default=DEFAULT_LEVEL, help="wind: strength of the wind reduction (default medium)"
    )
    parser.add_argument("--cutoff", required=False, type=float, help="wind: high-pass cutoff in Hz, 20 to 1000 (default from level: 80, 120 or 200)")
    parser.add_argument(
        "--reduction", required=False, type=float, help="wind, afftdn: noise reduction in dB, 0.01 to 97 (default from level: 6, 12 or 20)"
    )
    parser.add_argument(
        "--noise-floor", required=False, type=float, default=DEFAULT_NOISE_FLOOR, help="wind, afftdn: noise floor in dB, -80 to -20 (default -50)"
    )
    parser.add_argument("--model", required=False, help="arnndn: path of the RNN model file (eg std.rnnn)")
    parser.add_argument("--mix", required=False, type=float, default=DEFAULT_MIX, help="arnndn: mix of denoised signal, -1 to 1 (default 0.8)")
    kwargs = util.parse_media_args(parser, input_type=(fil.FileType.AUDIO_FILE, fil.FileType.VIDEO_FILE))
    inputs = kwargs["inputfiles"]
    if len(inputs) > 1 and kwargs.get("outputfile"):
        log.logger.error("-o can't be used with several input files")
        sys.exit(2)
    keep_name = kwargs.get("keepName", False)
    if keep_name and kwargs.get("outputfile"):
        log.logger.error("-o can't be used with --keepName")
        sys.exit(2)
    options = {
        "method": kwargs["method"],
        "level": kwargs["level"],
        "cutoff": kwargs.get("cutoff"),
        "reduction": kwargs.get("reduction"),
        "noise_floor": kwargs["noise_floor"],
        "model": kwargs.get("model"),
        "mix": kwargs["mix"],
    }
    try:
        build_filter(**options)
    except ValueError as e:
        log.logger.error("%s", e)
        sys.exit(2)

    def process(input_file: str, file_options: dict) -> None:
        util.generated_file(denoise(input_file, file_options.get("outputfile"), keep_name=keep_name, **options))

    util.process_input_files(kwargs, process)
    sys.exit(0)


if __name__ == "__main__":
    main()
