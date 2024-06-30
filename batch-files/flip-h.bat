setlocal enabledelayedexpansion

for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vf hflip -c:a copy "%%~F.hflip.mp4"
)

pause