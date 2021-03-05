#!/bin/bash

. lib-it.sh

for pos in top left center bottom-right top-right
do
    for box in 320x240 400x800 960x1080 1920x128 50%x100% 80%x50% 50%x10% 100%x100%
    do
        run_cmd "media-crop -i img-3000x4000.jpg  -o tmp/$f.crop.$pos.$box.jpg --box $box --position $pos"
    done
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm tmp/*.crop.* 2>/dev/null
exit 0
