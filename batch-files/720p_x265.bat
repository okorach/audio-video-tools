setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py --hw_accel -i "%%~F" -p 720p_x265 --vbitrate 3072k --width 1280 -o "%%~F.x265.720p.mp4" -g 5
)
