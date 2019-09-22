setlocal enabledelayedexpansion
for %%F in (%*) do (
    ..\encode.py -i "%%~F" -p 2mbps --vwidth 1280 -g 5
)