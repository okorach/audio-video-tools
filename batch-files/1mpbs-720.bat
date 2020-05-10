setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py -i "%%~F" -p 2mbps --width 720 --vbitrate 1024k -o "%%~F.1mbps.720x.mp4" -g 5
)
pause