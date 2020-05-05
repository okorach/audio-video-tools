set /p box=Box ?:
set /p top=Top ?:
set /p left=Left ?:
%~dp0\..\crop.py -i "%~1" --box %box% --top %left% --left %top% -g 2

rem pause