#!/bin/bash

. lib-it.sh

for f in *.mp4 *.mkv *.avi *.mov *.jpg *.gif *.png *.mp3 *.m4a *.wav *.ogg
do
    run_cmd "media-specs -i $f"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
exit 0
