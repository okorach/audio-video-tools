setlocal enabledelayedexpansion
for %%F in (%*) do (
    E:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -acodec aac -b:a 128k "%%~F.h265.1080p.auto.mp4"
)

::    E:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -an "%%~F.h265.auto.mp4"

pause