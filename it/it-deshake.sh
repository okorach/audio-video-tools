#!/bin/bash

for c in crop nocrop
do
    if [ "$c" = "crop" ]; then
        r=32
    else
        r=64
    fi
    cmd="video-stabilize -i video-1920x1080.mp4 --$c --rx $r --ry $r"
    echo "Running: $cmd"
    $cmd
    code=$?
    if [ $code -ne 0 ]; then
        1>&2 echo "FAILED: $cmd"
        exit $code
    fi
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm "./*.deshake*.mp4" 2>/dev/null
exit 0
