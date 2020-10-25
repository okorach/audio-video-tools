setlocal enabledelayedexpansion

for %%F in (%*) do (
    video-encode -i "%%~F" -p 1080p --width 1080 --vheight 1920 --aspect 9:16 --vbitrate 8192k -o "%%~F.1080p.mp4" -g 5
)
