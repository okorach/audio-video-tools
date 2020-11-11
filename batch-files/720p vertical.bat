setlocal enabledelayedexpansion

for %%F in (%*) do (
    video-encode -i "%%~F" -p 1080p --width 720 --vheight 1280 --aspect 9:16 --vbitrate 3072k -o "%%~F.720pV.mp4" -g 5
)
