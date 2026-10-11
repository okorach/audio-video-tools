:: Reduces the noise (focus on wind noise) of the audio of the files passed as argument, using audio-denoise
:: Methods: wind (default), afftdn, arnndn (neural network, uses the model D:\Tools\ffmpeg\bin\std.rnnn)
:: Wind method options (press Enter to keep the default):
::   Level: light, medium (default), strong
::   Cutoff: high-pass cutoff in Hz, default from the level (light 80, medium 120, strong 200)
::   Reduction: noise reduction in dB, default from the level (light 6, medium 12, strong 20)
::   Noise floor: estimated noise level in dB, default -50
:: Each file is replaced by the denoised file, the original is kept as <name>.before-denoise.<ext>

setlocal enabledelayedexpansion
set method=wind
set /p method=Method [wind, afftdn, arnndn] (default wind) ? 
if /i "!method!"=="arnndn" (
    set options=--method arnndn --model "D:\Tools\ffmpeg\bin\std.rnnn" --keepName
    goto run
)
set level=medium
set /p level=Level [light, medium, strong] (default medium) ? 
set cutoff=
set /p cutoff=Cutoff in Hz, 20 to 1000 (default from level) ? 
set reduction=
set /p reduction=Reduction in dB, 0.01 to 97 (default from level) ? 
set noise_floor=-50
set /p noise_floor=Noise floor in dB, -80 to -20 (default -50) ? 
set options=--method !method! --level !level! --noise-floor !noise_floor! --keepName
if defined cutoff set options=!options! --cutoff !cutoff!
if defined reduction set options=!options! --reduction !reduction!
:run
audio-denoise -i %* !options!
pause
