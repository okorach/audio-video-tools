#!/bin/bash

for res in 720x400 1280x720 1920x1080 3840x2160
do
    video-slideshow *.jpg --resolution $res -g 5
    code=$?
    if [ $code -ne 0 ]; then
        1>&2 echo "FAILED video-slideshow *.jpg --resolution $res"
        exit $code
    fi
done
