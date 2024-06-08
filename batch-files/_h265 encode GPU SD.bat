setlocal enabledelayedexpansion

set /p year=Good year ?

for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -cps 35 -vcodec "hevc_nvenc" -acodec aac -b:a 128k "%%~F.h265.auto.mp4"
    datefixer --year=%year% --files "%%~F" "%%~F.h265.auto.mp4"
)

::    D:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -vcodec "hevc_nvenc" -an "%%~F.h265.auto.mp4"

:: pause