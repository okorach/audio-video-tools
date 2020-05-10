setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py --hw_accel -i "%%~F" -p 2mbps --width 1280 -g 5
)
pause