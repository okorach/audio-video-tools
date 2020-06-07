setlocal enabledelayedexpansion
for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg -i "%%~F" -f mp4 -acodec aac -b:a 128k -vcodec libx264 -b:v 10000k -vf "transpose=2" "%%~F".rotate-90.mp4"
)
pause
