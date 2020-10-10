set /p start=Start ?
set /p stop=Stop ?

video-cut -i "%~1" --start %start% --stop %stop%

Pause
