setlocal enabledelayedexpansion

for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -vf reverse -c:a copy "%%~F.reverse.mp4"
)

pause