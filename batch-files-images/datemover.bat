:: setlocal enabledelayedexpansion

set /p year=Proper year ?
:: datefixer --year="%year%" --files %*
datefixer --mode year --year=%year% --files %*

:: pause