rem E:\Tools\ffmpeg-3.4-win64-static\bin\ffprobe -i %1 -show_entries -v quiet -of csv="p=0" >%1.txt
E:\Tools\ffmpeg\bin\ffprobe -v error -show_format -show_streams "%~1" >"%~1.txt"
pause