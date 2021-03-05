#!/bin/bash

rm -r tmp 2>/dev/null

. lib-it.sh

for cmd in it*.sh
do
    if [ "$cmd" != "$(basename $0)" -a "$cmd" != "it-01-image-crop.sh" -a "$cmd" != 'it-02-video-crop.sh' ]; then
        run_cmd "$cmd"
        echo "----------------------------------------"
        echo "SUCCESS: $cmd"
        echo "----------------------------------------"
    fi
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm -r tmp 2>/dev/null
exit 0
