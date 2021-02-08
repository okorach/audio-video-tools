#!/bin/bash

. lib-it.sh

run_cmd "image-to-video -i img-3000x4000.jpg --effect panorama --duration 5 --speed 3%"
run_cmd "image-to-video -i img-3000x4000.jpg --effect panorama --speed 10% --bounds 1,0,0.5,0.5"
run_cmd "image-to-video -i img-3000x4000.jpg --effect panorama --duration 5 --bounds 0,1,0.4,0.6"
run_cmd "image-to-video -i img-3000x4000.jpg --effect panorama -o img-3000x4000.2.pan.mp4 --duration 5 --bounds 0.7,0.4,0.4,0.6"
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.pan*.mp4 2>/dev/null
exit 0
