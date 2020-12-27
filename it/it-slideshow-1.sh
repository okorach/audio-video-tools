#!/bin/bash

for res in 720x400 1280x720 1920x1080 3840x2160
do
    cmd="video-slideshow *.jpg --resolution $res"
    $cmd
    code=$?
    if [ $code -ne 0 ]; then
        1>&2 echo "FAILED $cmd"
        exit $code
    fi
done
echo "----------------------------------------"
echo "SUCCESS" `basename $0`
echo "----------------------------------------"
rm *.pan*.mp4 *.zoom*.mp4 2>/dev/null
exit 0
