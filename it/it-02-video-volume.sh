#!/bin/bash

. lib-it.sh

for file in ./*.mp4
do
    for vol in 10% 25% 66% 200% 500% 4dB 8dB
    do
        run_cmd "media-volume -i $file --volume $vol -o video.volume.$vol.mp4"
    done
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.volume*.mp4 2>/dev/null
exit 0
