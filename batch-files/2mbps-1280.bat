setlocal enabledelayedexpansion
for %%F in (%*) do (
    video-encode --hw_accel -i "%%~F" -p 2mbps --width 1280 -o "%%~F.2mbps.1280x.mp4"
)
