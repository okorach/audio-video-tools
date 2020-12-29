#!/bin/bash
list=`ls *.jpg`
for f in $list
do
    for w in "" 64 128 258 512 500 800 1024 2000 3000 10000
    do
        for h in "" 64 128 258 512 500 800 1024 2000 3000 10000
        do
            if [ "$f" = "img-superwide.jpg" ] && [ "$h" = "10000"   ]; then
                continue
            fi
            cmd="image-scale -i $f -s ${w}x${h}"
            $cmd
            code=$?
            if [ $code -ne 0 ]; then
                1>&2 echo "FAILED: $cmd"
                exit $code
            fi
            rm "./$f*.scale-*.jpg" 2>/dev/null
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm ./*.scale-*.jpg 2>/dev/null
exit 0
