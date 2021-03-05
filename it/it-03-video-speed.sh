#!/bin/bash

. lib-it.sh

for speed in 10% 0.25 50% 200% 4 1000% 300%
do
    case $speed in
        10%|50%|4|300%)
            file=video-720p.mp4
            ;;
        *)
            file=video-1920x1080.mp4
            ;;
    esac
    case $speed in
        10%|200%|1000%)
            keep_audio="--keep_audio"
            ;;
        *)
            keep_audio=""
            ;;
    esac
    run_cmd "video-speed -i $file -o tmp/$file.speed.$speed.mp4 $keep_audio --speed $speed -o video.speed.$speed.mp4"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.speed.* 2>/dev/null
exit 0
