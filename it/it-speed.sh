#!/bin/bash

. lib-it.sh

for speed in 0.1x 0.25 0.5x 2x 4 10x 3x
do
    case $speed in
        0.1x|0.5x|4|3x)
            file=video-720p.mp4
            ;;
        *)
            file=video-1920x1080.mp4
            ;;
    esac
    case $speed in
        0.1x|2x|10x)
            keep_audio="--keep_audio"
            ;;
        *)
            keep_audio=""
            ;;
    esac
    run_cmd "video-speed -i $file $keep_audio --speed $speed -o video.speed.$speed.mp4"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.speed.*.mp4 2>/dev/null
exit 0
