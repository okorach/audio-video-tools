#!/bin/bash

. lib-it.sh

let i=0
for f in ./*.jpg
do
    for n in 2 7 11 17 29
    do
        for r in 1% 3% 7% 10 20
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
            run_cmd "image-blinds -i $f -o tmp/$f.blind.$n.$r.jpg -n $n -d $d -c $c -b $r"
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm ./*.blind.* tmp/*.blind.* 2>/dev/null
exit 0
