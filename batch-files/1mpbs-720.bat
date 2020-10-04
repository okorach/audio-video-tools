setlocal enabledelayedexpansion
for %%F in (%*) do (
    video-encode -i "%%~F" -p 2mbps --hw_accel --width 720 --vbitrate 1024k -o "%%~F.1mbps.720x.mp4" -g 5
)
