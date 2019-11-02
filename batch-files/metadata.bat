set /p year=Year of video?:

E:\Tools\ffmpeg\bin\ffmpeg -i "%~1" -vcodec copy -c:a copy -map 0 -metadata year=%year% -metadata copyright="(c) O. Korach %year%"  -metadata author="Olivier Korach" -metadata:s:a:0 language=fre -metadata:s:a:0 title="Avec musique" -metadata:s:a:1 language=fre -metadata:s:a:1 title="Sans musique" -metadata:s:v:0 language=fre -disposition:a:0 default -disposition:a:1 none "%~1.meta.mp4"

pause