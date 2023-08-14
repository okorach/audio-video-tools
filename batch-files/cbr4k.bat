setlocal enabledelayedexpansion
for %%F in (%*) do (
    :: x264  x264_10bit nvenc_h264 x265 x265_10bit x265_12bit nvenc_h265 nvenc_h265_10bit mpeg4
    :: C:\tools\handbrake\handbrakeCLI.exe -i "%%~F" -o "%%~F.cbr.mp4" -q 22 --cfr --vb 20000 -E copy:aac -f av_mp4 -e x264 
    C:\tools\handbrake\handbrakeCLI.exe -i "%%~F" -o "%%~F.cbr.mp4" -q 22 --cfr --vb 40000 -E copy:aac -f av_mp4 -e nvenc_h264 

)
