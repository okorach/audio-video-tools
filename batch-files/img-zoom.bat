setlocal enabledelayedexpansion
for %%F in (%*) do (
    image-to-video -g 5 --style zoom -i "%~1"
)