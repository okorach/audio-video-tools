:: setlocal enabledelayedexpansion

set /p offset=offset ?
datefixer --offset="%offset%" --files %*

pause
