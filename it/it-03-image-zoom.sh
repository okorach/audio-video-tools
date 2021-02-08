#!/bin/bash

. lib-it.sh

run_cmd "image-to-video -i img-3000x4000.jpg --effect zoom --duration 5 --bounds 1,1.3"
run_cmd "image-to-video -i img-3000x4000.jpg --effect zoom --duration 3 --bounds 1.2,1.0"
run_cmd "image-to-video -i img-3000x4000.jpg --effect zoom -o img-3000x4000.2.zoom.mp4 --effect zoom --duration 7 --bounds 1.1,1.3"
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.zoom*.mp4 2>/dev/null
exit 0
