set /p vbitrate=Video bitrate ?
set /p width=Video width ?
video-encode -i %1 -p 4mbps --vbitrate %vbitrate% --width %width% -g 1
pause