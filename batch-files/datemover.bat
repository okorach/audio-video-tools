:: setlocal enabledelayedexpansion

:: set /p year=Proper year ?
:: datefixer --year="%year%" --files %*
datefixer --year=2019 --files %*

:: pause