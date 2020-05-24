setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py --hw_accel -i "%%~F" -p 2mbps --width 1280 -o "%%~F.2mbps.1280x.mp4"
)
