setlocal enabledelayedexpansion
for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -vcodec libx265 -vcodec "hevc_nvenc" -acodec aac -b:a 128k -b:v 6M "%%~F.h265.auto.mp4"
)

::    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -an "%%~F.h265.auto.mp4"

:: pause