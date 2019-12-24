set /p year=Year of video?:

%~dp0\..\metadata.py -i "%~1" --year %year% --copyright "(c) O. Korach %year%"  --author "Olivier Korach" -o "%~1.meta.mp4"

pause