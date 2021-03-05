#!/bin/bash

. lib-it.sh

for f in ./*.jpg
do
    for w in "" 128 258 500 800 1024 2000 3000 10000
    do
        for h in "" 64 258 512 800 1024 2000 3000 10000
        do
            if [ "$f" = "./img-superwide.jpg" ] && [ "$h" = "10000" ]; then
                # Generates a too wide image, skip
                continue
            fi
            run_cmd "image-scale -i $f -o tmp/$f.scale.$w.$h.jpg -s ${w}x${h}"
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm tmp/*.scale.* 2>/dev/null
exit 0
