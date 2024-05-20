setlocal enabledelayedexpansion
for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -acodec aac -b:a 128k "%%~F.h265.auto.mp4"
    datefixer --year=2019 --files "%%~F" "%%~F.h265.auto.mp4"
)

::    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -an "%%~F.h265.auto.mp4"

:: pause