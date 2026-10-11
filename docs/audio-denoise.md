# audio-denoise

Reduces the noise of the audio of audio and video files, with a focus on **wind noise**. For video files the
video stream is copied unchanged and only the audio is re-encoded.

## Usage

```
audio-denoise -i <file> [<file> ...] [-o <output>] [--method wind|afftdn|arnndn] [--level light|medium|strong]
              [--cutoff <Hz>] [--reduction <dB>] [--noise-floor <dB>] [--model <file>] [--mix <-1..1>]
```

The output is `<input>.denoised.<ext>` unless `-o` is given (single input file only).

## Methods

### `wind` (default)

Wind noise is mostly low frequency rumble plus broadband gusts. This method chains:

1. a 2 poles **high-pass filter** that removes the rumble (`highpass=f=<cutoff>:poles=2`),
2. an adaptive **FFT denoiser with noise tracking** that follows the gusts (`afftdn=nr=<reduction>:nf=<noise floor>:tn=1`).

| `--level` | High-pass cutoff | Noise reduction |
|-----------|------------------|-----------------|
| `light` | 80 Hz | 6 dB |
| `medium` (default) | 120 Hz | 12 dB |
| `strong` | 200 Hz | 20 dB |

Use `light` to preserve low voices, `strong` for heavy wind (a high cutoff makes voices thinner).
`--cutoff` (20 to 1000 Hz) and `--reduction` (0.01 to 97 dB) override the level, `--noise-floor`
(-80 to -20 dB, default -50) sets the estimated noise level.

### `afftdn`

FFT denoiser only (no high-pass), for steady noises (fan, hiss...). `--reduction` defaults to 12 dB.

### `arnndn`

Recurrent neural network denoiser, better on speech. Requires a model file with `--model` (eg `std.rnnn` from
https://github.com/GregorR/rnnoise-models). `--mix` (-1 to 1, default 0.8) sets how much of the denoised
signal is used.

## Exit codes

- `0` all files processed
- `1` at least one file failed
- `2` invalid options (eg `--reduction 100`, `arnndn` without `--model`, `-o` with several inputs)

## Examples

```
# Reduce the wind noise of an action cam video
audio-denoise -i DJI_0031_D.MP4

# Heavy wind
audio-denoise -i DJI_0031_D.MP4 --level strong

# Custom: cut everything below 150 Hz and reduce by 15 dB
audio-denoise -i interview.mp4 --cutoff 150 --reduction 15 -o interview.clean.mp4

# Neural network denoiser
audio-denoise -i speech.wav --method arnndn --model std.rnnn
```
