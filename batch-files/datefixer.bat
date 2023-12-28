:: setlocal enabledelayedexpansion

set /p offset_plus=offset+ ?
set /p offset_minus=offset- ?
datefixer --add_time "%offset_plus%" --remove_time "%offset_minus%" --files %*
