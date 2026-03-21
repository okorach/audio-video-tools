#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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

"""
This script detects tune/song changes in a long audio file (e.g. DJ mix, live concert)
and splits it at those boundaries with fade-in/fade-out at each cut.
"""

import sys
from mediatools import log
import mediatools.utilities as util
import mediatools.audiofile as audio
import filters.filters as filters


def _checkerboard_kernel(M):
    """Builds a Gaussian-tapered checkerboard kernel (Foote 2000) of size 2M x 2M."""
    import numpy as np
    import scipy.signal

    g = scipy.signal.windows.gaussian(2 * M, std=M / 2.0, sym=True)
    G = np.outer(g, g)
    # Negate off-diagonal quadrants to create checkerboard pattern
    G[:M, M:] *= -1
    G[M:, :M] *= -1
    return G


def _novelty_from_ssm(ssm, kernel_size=64):
    """Computes a novelty curve by sliding a checkerboard kernel along the SSM diagonal."""
    import numpy as np

    kernel = _checkerboard_kernel(kernel_size)
    n = ssm.shape[0]
    novelty = np.zeros(n)
    for i in range(kernel_size, n - kernel_size):
        patch = ssm[i - kernel_size : i + kernel_size, i - kernel_size : i + kernel_size]
        novelty[i] = np.sum(patch * kernel)
    # Half-wave rectify and normalize
    novelty = np.maximum(novelty, 0)
    if novelty.max() > 0:
        novelty /= novelty.max()
    return novelty


def _detect_energy_gaps(y, sr, hop_length, min_gap_sec=2.0, energy_ratio=0.25):
    """Detects low-energy gaps (silence, applause lulls) between songs.

    Uses a local energy dip approach: instead of a global threshold, it looks for
    frames where the energy drops significantly compared to the surrounding context.
    This handles concerts where overall energy varies across the recording.
    """
    import librosa
    import numpy as np

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    # Smooth RMS over ~2 seconds to remove per-beat fluctuations
    smooth_frames = max(1, int(2.0 * sr / hop_length))
    rms_smooth = np.convolve(rms, np.ones(smooth_frames) / smooth_frames, mode="same")

    # Compute a local reference energy: smoothed over ~30 seconds (song-level context)
    local_ref_frames = max(1, int(30.0 * sr / hop_length))
    rms_local = np.convolve(rms, np.ones(local_ref_frames) / local_ref_frames, mode="same")

    # A gap is where short-term energy is well below local context
    is_gap = rms_smooth < rms_local * energy_ratio

    # Find contiguous gap regions
    diff = np.diff(is_gap.astype(int))
    gap_starts = np.where(diff == 1)[0] + 1
    gap_ends = np.where(diff == -1)[0] + 1
    if is_gap[0]:
        gap_starts = np.insert(gap_starts, 0, 0)
    if is_gap[-1]:
        gap_ends = np.append(gap_ends, len(is_gap))
    n_gaps = min(len(gap_starts), len(gap_ends))
    gap_starts = gap_starts[:n_gaps]
    gap_ends = gap_ends[:n_gaps]

    # Keep only gaps longer than min_gap_sec
    min_gap_frames = int(min_gap_sec * sr / hop_length)
    boundaries = []
    for s, e in zip(gap_starts, gap_ends):
        if e - s >= min_gap_frames:
            mid_frame = (s + e) // 2
            t = librosa.frames_to_time(mid_frame, sr=sr, hop_length=hop_length)
            gap_dur = (e - s) * hop_length / sr
            log.logger.info("  Energy gap: %.1fs - %.1fs (duration: %.1fs)", t - gap_dur / 2, t + gap_dur / 2, gap_dur)
            boundaries.append(t)
    return boundaries


def _detect_structural_boundaries(y, sr, hop_length, min_segment, sensitivity):
    """Detects structural boundaries using Foote's checkerboard novelty on beat-synced features."""
    import librosa
    import numpy as np
    import scipy.ndimage

    log.logger.info("Computing beat-synchronized features...")
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length, trim=False)

    # Extract and beat-synchronize features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
    spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop_length)

    chroma_sync = librosa.util.sync(chroma, beats, aggregate=np.median)
    mfcc_sync = librosa.util.sync(mfcc, beats, aggregate=np.median)
    contrast_sync = librosa.util.sync(spectral_contrast, beats, aggregate=np.median)

    features = np.vstack(
        [
            librosa.util.normalize(chroma_sync, axis=1),
            librosa.util.normalize(mfcc_sync, axis=1),
            librosa.util.normalize(contrast_sync, axis=1),
        ]
    )

    log.logger.info("Building self-similarity matrix (%d beat frames)...", features.shape[1])
    R = librosa.segment.recurrence_matrix(features, mode="affinity", sym=True, self=True, width=3)

    # Enhance with median filter in time-lag domain
    df = librosa.segment.timelag_filter(scipy.ndimage.median_filter)
    R = df(R, size=(1, 7))

    # Checkerboard kernel size: ~30-45 seconds is the sweet spot for detecting
    # song-level transitions (catches verse-to-applause or key changes between songs,
    # while ignoring within-song section changes like verse-to-chorus)
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=hop_length)
    if len(beat_times) > 1:
        avg_beat_dur = np.median(np.diff(beat_times))
    else:
        avg_beat_dur = 0.5
    target_window_sec = 40.0  # ~40 second analysis window
    kernel_size = max(16, int(target_window_sec / avg_beat_dur))
    # Cap kernel to avoid exceeding matrix size
    kernel_size = min(kernel_size, R.shape[0] // 4)
    log.logger.info("Foote kernel size: %d beat frames (avg beat: %.2fs, ~%.0fs window)", kernel_size, avg_beat_dur, kernel_size * avg_beat_dur)

    novelty = _novelty_from_ssm(R, kernel_size=kernel_size)

    # Peak picking: keep prominent novelty peaks
    # Higher sensitivity -> lower delta -> more peaks detected
    delta = 0.05 + (1.0 - sensitivity) * 0.25  # sensitivity 0.5 -> delta 0.175
    min_wait_beats = max(1, int(min_segment / avg_beat_dur))
    pre_post = max(1, min_wait_beats // 2)

    peaks = librosa.util.peak_pick(
        novelty, pre_max=pre_post, post_max=pre_post, pre_avg=pre_post, post_avg=pre_post, delta=delta, wait=min_wait_beats
    )

    # Convert beat-frame indices to timestamps
    boundaries = []
    for p in peaks:
        if p < len(beat_times):
            boundaries.append(float(beat_times[p]))

    return boundaries


def detect_tune_changes(filename, sensitivity=0.5, min_segment=30):
    """Detects song boundaries in a long audio file using two complementary methods:
    1. Energy-based gap detection (silence/applause between songs)
    2. Foote's checkerboard kernel novelty on beat-synced spectral features

    Args:
        filename: Path to the audio file
        sensitivity: 0.0-1.0, higher means more splits
        min_segment: Minimum segment duration in seconds

    Returns:
        List of boundary timestamps in seconds (excluding 0 and end)
    """
    import librosa
    import numpy as np

    log.logger.info("Loading audio file %s for analysis...", filename)
    y, sr = librosa.load(filename, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    log.logger.info("Audio duration: %.1f seconds (%.1f minutes)", duration, duration / 60)

    hop_length = 512

    # Signal 1: Energy-based gap detection (catches silence/applause between songs)
    # Uses local energy comparison: a gap is where energy drops below 25% of local context
    log.logger.info("Detecting energy gaps...")
    energy_boundaries = _detect_energy_gaps(y, sr, hop_length, min_gap_sec=2.0, energy_ratio=0.20 + sensitivity * 0.15)
    log.logger.info("Energy gaps found: %d", len(energy_boundaries))
    for b in energy_boundaries:
        log.logger.info("  Energy gap at %s (%.1fs)", util.to_hms_str(b), b)

    # Signal 2: Structural novelty via Foote's checkerboard kernel
    log.logger.info("Detecting structural boundaries...")
    structural_boundaries = _detect_structural_boundaries(y, sr, hop_length, min_segment, sensitivity)
    log.logger.info("Structural boundaries found: %d", len(structural_boundaries))
    for b in structural_boundaries:
        log.logger.info("  Structural boundary at %s (%.1fs)", util.to_hms_str(b), b)

    # Merge: energy boundaries are high-confidence, structural boundaries add coverage
    # For each structural boundary, keep it only if no energy boundary is already nearby
    merge_window = min_segment / 2
    all_boundaries = list(energy_boundaries)
    for sb in structural_boundaries:
        if not any(abs(sb - eb) < merge_window for eb in all_boundaries):
            all_boundaries.append(sb)

    all_boundaries.sort()

    # Filter: remove boundaries too close to start/end, enforce min_segment spacing
    filtered = []
    for b in all_boundaries:
        if b < min_segment or b > duration - min_segment:
            continue
        if filtered and b - filtered[-1] < min_segment:
            continue
        filtered.append(b)

    log.logger.info("Final merged boundaries: %d", len(filtered))
    for i, b in enumerate(filtered):
        log.logger.info("  Boundary %d: %s (%.1f s)", i + 1, util.to_hms_str(b), b)

    return filtered


def split_audio_at_boundaries(input_file, boundaries, fade_duration=1.0):
    """Splits an audio file at the given boundary timestamps with fade effects.

    Args:
        input_file: Path to the input audio file
        boundaries: List of split points in seconds
        fade_duration: Duration of fade-in/fade-out in seconds

    Returns:
        List of output file paths
    """
    af = audio.AudioFile(input_file)
    af.get_specs()
    total_duration = af.duration

    # Preserve original bitrate in split files
    bitrate_opt = f"-b:a {af.abitrate}" if af.abitrate else ""

    # Build segments: [0, b1], [b1, b2], ..., [bN, end]
    starts = [0.0] + boundaries
    ends = boundaries + [total_duration]

    output_files = []
    for i, (start, end) in enumerate(zip(starts, ends)):
        segment_duration = end - start
        postfix = f"split{i + 1:03d}"
        outputfile = util.automatic_output_file_name(outfile=None, infile=input_file, postfix=postfix)

        # Build audio filter chain
        audio_filters = []
        is_first = i == 0
        is_last = i == len(starts) - 1

        if not is_first:
            audio_filters.append(filters.afade_in(start=0, duration=fade_duration))
        if not is_last:
            fade_out_start = max(0, segment_duration - fade_duration)
            audio_filters.append(filters.afade_out(start=fade_out_start, duration=fade_duration))

        af_str = ""
        if audio_filters:
            af_str = f'-af "{",".join(audio_filters)}"'

        cmd = f'-ss {start} -i "{input_file}" -t {segment_duration} {bitrate_opt} {af_str} "{outputfile}"'
        log.logger.info("Generating segment %d/%d: %s -> %s (%s)", i + 1, len(starts), util.to_hms_str(start), util.to_hms_str(end), outputfile)
        util.run_ffmpeg(cmd, duration=segment_duration)
        util.generated_file(outputfile)
        output_files.append(outputfile)

    return output_files


def main():
    parser = util.get_common_args("audio-split", "Splits a long audio file at detected tune/song changes with fade effects")
    parser.add_argument("--fade-duration", required=False, type=float, default=1.0, help="Fade in/out duration in seconds (default: 1.0)")
    parser.add_argument("--min-segment", required=False, type=float, default=120.0, help="Minimum segment duration in seconds (default: 120)")
    parser.add_argument(
        "--sensitivity", required=False, type=float, default=0.5, help="Detection sensitivity 0.0-1.0, higher = more splits (default: 0.5)"
    )
    parser.add_argument("--dry-run", required=False, default=False, action="store_true", help="Only detect and print change points, do not split")

    kwargs = util.parse_media_args(parser)
    input_file = kwargs.pop("inputfiles")[0]
    fade_duration = kwargs.get("fade_duration", 1.0)
    min_segment = kwargs.get("min_segment", 30.0)
    sensitivity = kwargs.get("sensitivity", 0.5)
    dry_run = kwargs.get("dry_run", False)

    if sensitivity < 0.0 or sensitivity > 1.0:
        log.logger.error("Sensitivity must be between 0.0 and 1.0")
        sys.exit(1)

    boundaries = detect_tune_changes(input_file, sensitivity=sensitivity, min_segment=min_segment)

    if not boundaries:
        log.logger.warning("No tune changes detected. Try increasing --sensitivity or decreasing --min-segment.")
        print("No tune changes detected.")
        return

    print(f"Detected {len(boundaries)} tune change(s):")
    for i, b in enumerate(boundaries):
        print(f"  {i + 1}. {util.to_hms_str(b)} ({b:.1f}s)")

    if dry_run:
        print("Dry run mode - no files generated.")
        return

    output_files = split_audio_at_boundaries(input_file, boundaries, fade_duration=fade_duration)
    print(f"Generated {len(output_files)} segment(s).")


if __name__ == "__main__":
    main()
