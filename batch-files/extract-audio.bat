setlocal enabledelayedexpansion
for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg.exe -i "%%~F" -vn -codec copy "%%~F.m4a"
)

pause