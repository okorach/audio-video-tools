#!/bin/bash
for pos in top left center bottom-right top-right
do
     for box in 320x240 400x800 960x1080 1920x128 50%x100% 80%x50% 50%x50%
     do
         video-crop -i video-1920x1080.mp4 --box $box --position $pos
         code=$?
         if [ $code -ne 0 ]; then
             1>&2 echo FAILED video-crop -i video-1920x1080.mp4 --box $box --position $pos
             exit $code
         fi
     done
done
echo "SUCCESS video-crop"
rm *.crop_*.mp4
exit 0
