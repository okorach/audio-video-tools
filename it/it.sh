#!/bin/bash

. lib-it.sh

rm ./*.blind.jpg ./*.log ./*.pan*.mp4 ./*.zoom*.mp4 ./*.crop_*.* ./*.deshake*.mp4 ./*.encode.*.mp4 ./*.scale-*.jpg 2>/dev/null
for cmd in it*.sh
do
    if [ "$cmd" != "$(basename $0)" ]; then
        run_cmd "$cmd"
        echo "----------------------------------------"
        echo "SUCCESS: $cmd"
        echo "----------------------------------------"
    fi
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
exit 0
