setlocal enabledelayedexpansion

for %%F in (%*) do (
    encodeauto -g 5 -i "%%~F" --nooverwrite --before " " --after "-af arnndn=model='\\tools\\ffmpeg\\bin\\std.rnnn:mix=0.8' -c:a aac -b:a 128k -c:v copy"
)

"D:\Tools\ffmpeg\bin\ffmpeg" -y   -i "D:\\2003 - Julie à la maternité.mp4" -af arnndn=model='\\tools\\ffmpeg\\bin\\std.rnnn:mix=0.8' -c:a aac -b:a 128k -c:v copy "D:\\2003 - Julie à la maternité.encode.00.mp4"

pause