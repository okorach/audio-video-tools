setlocal enabledelayedexpansion

for %%F in (%*) do (
    D:\tools\ffmpeg\bin\ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "%%~F" -filter:v "bwdif_cuda=mode=send_frame:parity=tff:deint=interlaced" -vcodec hevc_nvenc -c:a copy "%%~F.deint.mp4"
)

pause