set /p vbitrate=Video bitrate ? 
set /p width=Video width ? 
%~dp0\..\encode.py -i %1 -p 4mbps --vbitrate %vbitrate% --width %width% -g 1
pause