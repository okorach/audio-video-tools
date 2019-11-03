setlocal enabledelayedexpansion
for %%F in (%*) do (
    %~dp0\..\encode.py -i "%%~F" -p 1080p --vwidth 1920 --vbitrate 16000k -g 5
)