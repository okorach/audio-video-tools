setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py -i "%%~F" -p 2mbps --hw_accel --width 960 --vbitrate 1200k -o "%%~F.1mbps.960x.mp4" -g 5
)
