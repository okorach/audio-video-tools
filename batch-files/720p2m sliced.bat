set /p timeranges=Time ranges ?

video-encode -i %1 -p 720p2m -g 5 -t %timeranges% --fade 2

pause
