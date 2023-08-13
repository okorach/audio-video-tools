:: setlocal enabledelayedexpansion
:: set /p root=Root name ?:
:: for %%F in (%*) do (
::    renamer -f "%%~F" -r "%root%"
:: )

:: renamer -r "%root%" -f %* -g 5
set /p seqstart=Sequence Start ?:
renamer --seqstart %seqstart% --format "Andalousie 2023 - #SEQ4# - #TIMESTAMP# - #DEVICE#" --files %*
pause
