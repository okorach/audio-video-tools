setlocal enabledelayedexpansion
for %%F in (%*) do (
    C:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -acodec aac -b:a 96k "%%~F.h265.1080p.auto.mp4"
)

::    C:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -an "%%~F.h265.auto.mp4"

pause