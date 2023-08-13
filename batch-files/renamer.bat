:: setlocal enabledelayedexpansion
set /p format=XXX - #SEQx# - #TIMESTAMP# - #DEVICE# - #SIZE# - #FPS#fps - #BITRATE# ?
:: for %%F in (%*) do (
::    renamer -f "%%~F" -r "%root%"
:: )

:: renamer -r "%root%" -f %* -g 5
set /p seqstart=Sequence Start ?
renamer --seqstart %seqstart% --format "%format%" --files %*
pause
