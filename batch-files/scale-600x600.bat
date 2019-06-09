E:\Tools\ffmpeg\bin\ffmpeg -i %1 -vf scale=600:600 %1-scaled.jpg
del %1
rename %1-scaled.jpg %1