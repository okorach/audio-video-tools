set /p vbitrate=Video bitrate ? 
set /p vwidth=Video width ? 
%~dp0\..\encode.py -i %1 -p 4mbps --vbitrate %vbitrate% --vwidth %vwidth% -g 1
pause