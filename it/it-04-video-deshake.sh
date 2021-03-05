#!/bin/bash

. lib-it.sh

for c in crop nocrop
do
    if [ "$c" = "crop" ]; then
        r=32
    else
        r=64
    fi
    run_cmd "video-stabilize -i video-1920x1080.mp4 -o tmp/video-1920x1080.deshake.$c.mp4 --$c --rx $r --ry $r"
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm tmp/*.deshake.* 2>/dev/null
exit 0
