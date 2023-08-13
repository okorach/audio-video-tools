:: setlocal enabledelayedexpansion
set /p prefix=Prefix ? 
set /p seq=Sequence digits ? 
:: for %%F in (%*) do (
::    renamer -f "%%~F" -r "%root%"
:: )

:: renamer -r "%root%" -f %* -g 5
set /p seqstart=Sequence Start ? 
renamer --seqstart %seqstart% --format "%prefix% - #SEQ%seq%# - #TIMESTAMP# - #DEVICE# - #SIZE# - #FPS#fps - #BITRATE#" -g 5 --files %*
pause
