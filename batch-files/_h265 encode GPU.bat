setlocal enabledelayedexpansion

:: set /p year=Good year ?

for %%F in (%*) do (
    video-encode -i "%%~F" --hw_accel on -p auto --vcodec x265 --acodec aac --abitrate 128k
)


:: "D:\tools\ffmpeg\bin\ffmpeg" -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F.original.mp4" -vcodec "hevc_nvenc" -acodec aac -b:a 128k "%%~F.mp4"
:: "D:\tools\ffmpeg\bin\ffmpeg" -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F.original.mp4" -vcodec "hevc_nvenc" -acodec aac -b:a 128k "%%~F.mp4"

::    D:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -vcodec "hevc_nvenc" -an "%%~F.h265.auto.mp4"

pause