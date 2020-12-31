#!/bin/bash

. lib-it.sh

for file in ./*.mp4
do
    video-metadata -i "$file" --copyright "Olivier Korach 2020" --author "O.Korach"
    code=$?
    if [ $code -ne 0 ]; then
        1>&2 echo "========================================"
        1>&2 echo "FAILED: video-metadata -i \"$file\" --copyright \"Olivier Korach 2020\" --author \"O.Korach\""
        1>&2 echo "========================================"
        exit $code
    fi
    for c in "OlivierKorach2020" "Oli.vier"
    do
        for lang in "0:fre" "0:fre:Francais sans sous-titre"  "0:eng:English with music"
        do
            run_cmd "video-metadata -i \"$file\" --copyright \"$c\" --author \"O.Korach\" --year \"2020\" --default_track 0 --language \"$lang\""
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.meta.mp4 2>/dev/null
exit 0

