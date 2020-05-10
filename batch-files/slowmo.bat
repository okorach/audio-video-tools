setlocal enabledelayedexpansion
set /p speed=Speed factor ?:
Rem -an removes audio
for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg.exe -i "%%~F" -filter:v "setpts=%speed%*PTS" -an -vcodec libx264 -b:v 6000k "%%~F.slowmo.%speed%.mp4"
)
pause