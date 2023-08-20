:: setlocal enabledelayedexpansion
:: set /p pformat=Photo format XXX - #SEQ# - #TIMESTAMP# - #DEVICE# - #SIZE# ?
:: set /p vformat=Video format XXX - #SEQ# - #TIMESTAMP# - #DEVICE# - #SIZE# - #FPS#fps - #BITRATE#MB ?
:: for %%F in (%*) do (
::    renamer -f "%%~F" -r "%root%"
:: )

:: renamer -r "%root%" -f %* -g 5
set /p prefix=Prefix ?
set /p seqstart=Sequence Start ?
renamer --seqstart %seqstart% --prefix "%prefix%" --photo_format "%prefix%" --video_format "%prefix%" --files %*
pause
