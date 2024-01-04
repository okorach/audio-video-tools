:: setlocal enabledelayedexpansion
set /p coord=GPS coordinates ?:
E:\tools\exiftool -gpsposition="%coord%" %*
