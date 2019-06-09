set /p speed=Speed factor ?:

Rem -an removes audio
E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i %1 -filter:v "setpts=%speed%*PTS" -an -vcodec libx264  %1.slowmo.%speed%.mp4



