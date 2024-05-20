setlocal enabledelayedexpansion
for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -vcodec "hevc_nvenc" -acodec aac -b:a 128k "%%~F.h265.auto.mp4"
    datefixer --year=2019 --files "%%~F" "%%~F.h265.auto.mp4"
)

::    D:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -vcodec "hevc_nvenc" -an "%%~F.h265.auto.mp4"

:: pause