set /p year=Year of video?:

E:\Tools\ffmpeg\bin\ffmpeg -i %1 -metadata year=%year% -metadata copyright="(c) O. Korach %year%" -c copy  -metadata author="Olivier Korach" -metadata:s:a:0 language=fre -metadata:s:v:0 language=fre %1.meta.mp4

set /p debug=Enter to quit: