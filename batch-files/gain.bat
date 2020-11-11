setlocal enabledelayedexpansion
for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg -i "%%~F" -f mp4 -acodec aac -b:a 128k -filter:a "volume=4" -vcodec copy "%%~F".gain.mp4"
)
pause
