setlocal enabledelayedexpansion

for %%F in (%*) do (
    video-encode --hw_accel -i "%%~F" -p 1080p_x265 --width 1920 --vbitrate 6144k -o "%%~F.x265.1080p.mp4" -g 5
)
