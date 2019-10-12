set /p timeranges=Time ranges ? 

%~dp0\..\encode.py -i %1 -p 720p2m -g 5 -t %timeranges% --fade 4

pause
