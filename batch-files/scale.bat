setlocal enabledelayedexpansion
set /p scale=Max size ?:
for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg -i "%%~F" -vf scale=%scale%:-1 "%%~F-%scale%.jpg"
)