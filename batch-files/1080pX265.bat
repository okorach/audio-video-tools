setlocal enabledelayedexpansion

for %%F in (%*) do (
    %~dp0\..\encode.py --hw_accel -i "%%~F" -p 1080p6mX265 --width 1920 --vbitrate 6144k -g 5
)
pause