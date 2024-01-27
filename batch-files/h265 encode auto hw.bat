setlocal enabledelayedexpansion
for %%F in (%*) do (
    :: -vf "scale_cuda=1920:-1"   -f "mp4" -b:a "128k" -b:v "6144k" -vcodec "hevc_nvenc"
    E:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -vcodec "hevc_nvenc" -acodec aac -b:a 128k "%%~F.hw.h265.auto.mp4"
)

::    E:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vcodec libx265 -an "%%~F.h265.auto.mp4"

pause