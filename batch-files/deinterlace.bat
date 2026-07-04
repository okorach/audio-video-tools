setlocal enabledelayedexpansion

for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -i "%%~F" -filter:v "bwdif=mode=send_field:parity=auto:deint=all" -c:a copy "%%~F.deint.mp4"
)

