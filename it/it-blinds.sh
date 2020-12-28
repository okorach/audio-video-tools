#!/bin/bash
for f in ./*.jpg
do
    for n in 2 5 10 17 29
    do
        for d in horizontal vertical
        do
            for c in black white
            do
                for r in 1 3 5 9
                do
                    cmd="image-blinds -i $f -n $n -d $d -c $c -r $r"
                    echo "Running: $cmd"
                    $cmd
                    code=$?
                    if [ $code -ne 0 ]; then
                        1>&2 echo "FAILED: $cmd"
                        exit $code
                    fi
                done
            done
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm ./*.blind.jpg 2>/dev/null
exit 0
