setlocal enabledelayedexpansion
set /p coord=GPS coordinates ?:
for %%F in (%*) do (
    E:\tools\exiftool -gpsposition="%coord%" "%%~F"
)
