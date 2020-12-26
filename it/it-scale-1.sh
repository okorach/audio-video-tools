#!/bin/bash
list=`ls *.jpg`
for f in $list
do
    for w in "" 64 128 258 512 500 800 1024 2000 3000 10000
    do
        for h in "" 64 128 258 512 500 800 1024 2000 3000 10000
        do
            image-scale -i $f -s "${w}x${h}"
            code=$?
            if [ $code -ne 0 ]; then
                1>&2 echo FAILED image-scale -i $f -s "${w}x${h}"
                rm *.scale-*.jpg
                exit $code
            fi
        done
    done
done
echo "SUCCESS image-scale"
rm *.scale-*.jpg
exit 0
