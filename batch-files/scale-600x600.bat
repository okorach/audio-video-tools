setlocal enabledelayedexpansion
for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg -i "%%~F" -vf scale=600:600 "%%~F-scaled.jpg"
    del "%~1"
    rename "%%~F-scaled.jpg" "%%~F"
)