setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py --hw_accel -i "%%~F" -p 2mbps --vbitrate 4096k --vwidth 1280 -o "%%~F.4mbps.1280x.mp4" -g 5
)
pause