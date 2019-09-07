setlocal enabledelayedexpansion
set /p speed=Speed factor ?:
Rem -an removes audio
for %%F in (%*) do (
    echo E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i "%%~F" -vf select='not(mod(n,%speed%))',setpts=N/FRAME_RATE/TB -an -vcodec libx264 -b:v 12288k "%%~F.timelapse.mp4"
    E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i "%%~F" -vf select='not(mod(n,%speed%))',setpts=N/FRAME_RATE/TB -an -vcodec libx264 -b:v 12288k "%%~F.timelapse.mp4"
    rem E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i %1 -vf framestep=%speed%,setpts=N/FRAME_RATE/TB %1.timelapse.mp4
)
set /p debug=Enter to quit:


