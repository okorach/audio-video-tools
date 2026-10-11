:: Reduces the noise (focus on wind noise) of the audio of the files passed as argument, using audio-denoise
:: Methods: wind (default), afftdn, arnndn (neural network, uses the model D:\Tools\ffmpeg\bin\std.rnnn)
:: Levels (wind method only): light, medium (default), strong
:: Each file is replaced by the denoised file, the original is kept as <name>.before-denoise.<ext>

setlocal enabledelayedexpansion
set method=wind
set /p method=Method [wind, afftdn, arnndn] (default wind) ? 
set level=medium
set /p level=Level [light, medium, strong] (default medium) ? 
set options=--method !method! --level !level! --keepName
if /i "!method!"=="arnndn" set options=!options! --model "D:\Tools\ffmpeg\bin\std.rnnn"
for %%F in (%*) do (
    audio-denoise -i "%%~F" !options!
)
pause
