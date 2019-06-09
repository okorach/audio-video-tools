set /p scale=Max size ?:
E:\Tools\ffmpeg\bin\ffmpeg -i %1 -vf scale=%scale%:-1 %1-%scale%.jpg
