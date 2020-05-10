set /p box=Box ?:
set /p top=Top ?:
set /p left=Left ?:
set /p range=Range ?:
if %range% == "" (
    %~dp0\..\crop.py -i "%~1" --box %box% --top %left% --left %top% -g 2
) else (
    %~dp0\..\crop.py -i "%~1" --timerange %range% --box %box% --top %left% --left %top% -g 2
)
pause