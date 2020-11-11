set /p box=Box ?:
set /p top=Top ?:
set /p left=Left ?:
set /p range=Range ?:
if %range% == "" (
    video-crop -i "%~1" --box %box% --top %left% --left %top% -g 5
) else (
    video-crop -i "%~1" --timerange %range% --box %box% --top %left% --left %top% -g 5
)
pause