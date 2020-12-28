#!/bin/bash

let i=0
for f in ./*.jpg
do
    for n in 2 7 11 17 29
    do
        for r in 1 3 7
        do
            let i=$i+1
            let k=(3*$i+1)%2
            if [ "$k" == "0" ]; then
                d=horizontal
            else
                d=vertical
            fi
            let k=(7*$i)%2
            if [ "$k" == "0" ]; then
                c=black
            else
                c=white
            fi
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
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm ./*.blind.jpg 2>/dev/null
exit 0
