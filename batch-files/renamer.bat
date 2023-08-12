:: setlocal enabledelayedexpansion
:: set /p root=Root name ?:
:: for %%F in (%*) do (
::    renamer -f "%%~F" -r "%root%"
:: )

:: renamer -r "%root%" -f %* -g 5
renamer -f %*
