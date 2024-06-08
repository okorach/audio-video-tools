setlocal enabledelayedexpansion

set /p year=Good year ?

for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -acodec aac -b:a 128k "%%~F.h265.auto.mp4"
    datefixer --year=%year% --files "%%~F" "%%~F.h265.auto.mp4"
)

::    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -an "%%~F.h265.auto.mp4"

:: pause