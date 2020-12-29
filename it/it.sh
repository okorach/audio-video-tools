#!/bin/bash

. lib-it.sh

for cmd in it*.sh
do
    if [ "$cmd" != "$(basename $0)" ]; then
        run_cmd "$cmd"
        echo "----------------------------------------"
        echo "SUCCESS: $cmd"
        echo "----------------------------------------"
    fi
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
exit 0
