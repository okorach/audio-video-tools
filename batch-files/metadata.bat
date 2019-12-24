set /p year=Year of video?: 
set /p track=Default track?: 
%~dp0\..\metadata.py -i "%~1" --year %year% --copyright "(c) O. Korach %year%" --author "Olivier Korach" --default_track %track% --languages "0:fre" "1:fre" --titles "0:Francais avec musique" "1:Francais sans musique" -o "%~1.meta.mp4"

pause