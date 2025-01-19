:: setlocal enabledelayedexpansion

set /p datestamp=Datestamp ?
datefixer --offset="%datestamp%" --files %*
