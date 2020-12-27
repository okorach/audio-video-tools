#!/bin/bash
for pos in top left center bottom-right top-right
do
    for box in 320x240 400x800 960x1080 1920x128 50%x100% 80%x50% 50%x50%
    do
        cmd="media-crop -i img-3000x4000.jpg --box $box --position $pos"
        $cmd
        code=$?
        if [ $code -ne 0 ]; then
            1>&2 echo "========================================"
            1>&2 echo "FAILED: $cmd"
            1>&2 echo "========================================"
            exit $code
        fi
    done
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.crop_*.jpg 2>/dev/null
exit 0
