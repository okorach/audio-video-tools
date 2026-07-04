:: setlocal enabledelayedexpansion

set /p datestamp=Datestamp ?
datefixer --mode absolute --offset="%datestamp%" --files %*

pause