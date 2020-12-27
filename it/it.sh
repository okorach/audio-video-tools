#!/bin/bash
for cmd in it*.sh
do
    if [ "$cmd" != "`basename $0`" ]; then
        $cmd
        code=$?
        if [ $code -ne 0 ]; then
            1>&2 echo "========================================"
            1>&2 echo $cmd
            1>&2 echo "========================================"
            exit $code
        fi
        echo "----------------------------------------"
        echo "SUCCESS" $cmd
        echo "----------------------------------------"
    fi
done
echo "----------------------------------------"
echo "SUCCESS" `basename $0`
echo "----------------------------------------"
rm *.crop_*.jpg 2>/dev/null
exit 0
