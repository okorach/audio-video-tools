rem E:\Tools\ffmpeg-3.4-win64-static\bin\ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" %1.mp3

album_art.pl -s %1 -g 5