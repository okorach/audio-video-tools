#!/bin/bash

. lib-it.sh

for vb in 2048k 1024k 512k
do
    case $vb in
        "512k")
            ab="32k"
            r="15"
            ;;
        "1024k")
            ab="64k"
            r="30"
            ;;
        *)
            ab="128k"
            r="60"
            ;;
    esac
    run_cmd "video-encode -i video-1920x1080.mp4 -o tmp/video-1920x1080.encode.$vb.mp4 -r $r --abitrate $ab --vbitrate $vb --width 1280 -o video.encode.$vb.mp4 -p 2mbps"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm tmp/*.encode.* 2>/dev/null
exit 0
