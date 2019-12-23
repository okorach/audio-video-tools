E:\Tools\ffmpeg\bin\ffmpeg -i "%~1" -f mp4 -acodec aac -b:a 128k -vcodec libx264 -b:v 10000k -vf "transpose=2" "%~1.rotate90.mp4"

pause