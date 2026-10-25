:: setlocal enabledelayedexpansion

set /p year=Proper year ?
:: datefixer --year="%year%" -i %*
datefixer --mode year --year=%year% -i %*
