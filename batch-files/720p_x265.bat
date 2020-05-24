setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py --hw_accel -i "%%~F" -p 720p3mX265 --vbitrate 3072k --width 1280 -o "%%~F.x265.1280x.mp4" -g 5
)
pause