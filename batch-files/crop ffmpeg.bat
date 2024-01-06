
set /p top=Top ?:
set /p left=Left ?:
set /p width=width ?:
set /p height=height ?:

E:\tools\ffmpeg\bin\ffmpeg -y -i "%~1" -filter:v "crop=%width%:%height%:%left%:%top%" "%~1.crop.mp4"
