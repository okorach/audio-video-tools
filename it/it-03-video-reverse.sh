#!/bin/bash

. lib-it.sh

for file in ./*.mp4
do
    for keep_audio in "" "--keep_audio"
    do
        run_cmd "video-reverse -i $file -o tmp/$file.reverse.mp4 $keep_audio"
    done
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm tmp/*.reverse.* 2>/dev/null
exit 0