:: setlocal enabledelayedexpansion

set /p datestamp=Datestamp ?
datefixer --mode offset --offset="%datestamp%" --files %*

pause