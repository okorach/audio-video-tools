#!/bin/bash

. lib-it.sh

for f in ./*.mp4
do
    run_cmd "video-cut -i $f --start 00:00 --stop 00:05"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.encode.*.mp4 2>/dev/null
exit 0
