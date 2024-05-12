setlocal enabledelayedexpansion
for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -aspect 4:3 -acodec aac -b:a 128k "%%~F.h265.1080p.auto.mp4"
)

::    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -an "%%~F.h265.auto.mp4"

:: pause