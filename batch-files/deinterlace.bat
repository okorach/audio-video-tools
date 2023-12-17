for %%F in (%*) do (
    E:\Tools\ffmpeg\bin\ffmpeg -i "%%~F" -vf yadif -c:v libx264 -preset slow -crf 19 "%%~F-deint.mp4"
)
