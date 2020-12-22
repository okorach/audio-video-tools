#!/bin/bash

echo "Max width ?:"
read width
for f in $*
do
    ~/bin/ffmpeg -i $f -vf scale=$width:-1 "$f-$width.jpg"
done