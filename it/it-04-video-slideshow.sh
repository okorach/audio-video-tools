#!/bin/bash

. lib-it.sh

res_list="$*"
if [ "$res_list" == "" ]; then
    res_list="360x200 720x400 1280x720 1920x1080 3840x2160"
fi

for res in $res_lsit
do
    run_cmd "video-slideshow *.jpg --resolution $res"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.pan*.mp4 ./*.zoom*.mp4 2>/dev/null
exit 0
