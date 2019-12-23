setlocal enabledelayedexpansion
set /p speed=Speed factor ?:
Rem -an removes audio
for %%F in (%*) do (
    E:\Tools\ffmpeg-20180928-win64\bin\ffmpeg.exe -i "%%~F" -filter:v "setpts=%speed%*PTS" -an -vcodec libx264  "%%~F.slowmo.%speed%.mp4"
)
