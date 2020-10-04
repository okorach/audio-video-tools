setlocal enabledelayedexpansion
for %%F in (%*) do (
    video-encode --hw_accel -i "%%~F" -p 2mbps --vbitrate 4096k --width 1280 -o "%%~F.4mbps.1280x.mp4"
)
