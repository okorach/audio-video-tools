E:\Tools\ffmpeg\bin\ffmpeg -i "%~1" -f mp4 -acodec aac -b:a 64k -vcodec libx264 -b:v 800k "%~1.640x480.mp4"

pause