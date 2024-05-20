:: setlocal enabledelayedexpansion
set /p coord=GPS coordinates ?:
D:\tools\exiftool -gpsposition="%coord%" %*
