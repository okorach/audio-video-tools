setlocal enabledelayedexpansion
for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg.exe -i "%%~F" -map 0:1 -vn -codec copy "%%~F.m4a"
)
