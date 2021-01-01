setlocal enabledelayedexpansion
for %%F in (%*) do (
    :: video-stabilize -i file -rx 64 -ry 64 -o outfile [--crop|--nocrop]
    video-stabilize -i "%%~F"
)
pause