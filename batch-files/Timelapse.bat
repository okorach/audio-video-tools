set /p speed=Speed factor ?:

echo E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i %1 -vf select='not(mod(n,%speed%))',setpts=N/FRAME_RATE/TB -an -vcodec libx264 -b:v 12288k %1.timelapse1.mp4

Rem -an removes audio
E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i %1 -vf select='not(mod(n,%speed%))',setpts=N/FRAME_RATE/TB -an -vcodec libx264 -b:v 12288k %1.timelapse.mp4
rem E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i %1 -vf framestep=%speed%,setpts=N/FRAME_RATE/TB %1.timelapse.mp4

set /p debug=Enter to quit:


