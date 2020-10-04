setlocal enabledelayedexpansion
for %%F in (%*) do (
    video-encode -i "%%~F" -p mp3_192k
)
