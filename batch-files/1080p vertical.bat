setlocal enabledelayedexpansion

for %%F in (%*) do (
    video-encode --hw_accel -i "%%~F" -p 1080p --width 1080 --vbitrate 8192k -o "%%~F.1080p.mp4" -g 5
)
