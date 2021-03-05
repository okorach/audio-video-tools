#!/bin/bash

. lib-it.sh

for pos in top left center bottom-right top-right
do
    for box in 320x240 400x800 960x1080 1920x128 50%x100% 80%x50% 50%x50%
    do
        run_cmd "media-crop -i video-1920x1080.mp4 -o tmp/video-1920x1080.crop.$box.mp4 --box $box --position $pos"
    done
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.crop.mp4 2>/dev/null
exit 0
