
::set /p top=Top ?:
::set /p left=Left ?:
::set /p width=width ?:
::set /p height=height ?:

C:\tools\ffmpeg\bin\ffmpeg -y -i "%~1" -vcodec libx265 -b:v 2048k -filter:v "crop=1675:928:0:68" "%~1.crop.mp4"
