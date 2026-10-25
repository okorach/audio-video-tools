#!/bin/bash

#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

. lib-it.sh

for file in ./*.mp4
do
    videotool metadata -i "$file" -o "tmp/$file.meta.1.mp4" --copyright "Olivier Korach 2020" --author "O.Korach"
    code=$?
    if [[ $code -ne 0 ]]; then
        1>&2 echo "========================================"
        1>&2 echo "FAILED: videotool metadata -i \"$file\" -o \"tmp/$file.meta.1.mp4\" --copyright \"Olivier Korach 2020\" --author \"O.Korach\""
        1>&2 echo "========================================"
        exit $code
    fi
    for c in "OlivierKorach2020" "Oli.vier"
    do
        for lang in "0:fre" "0:fre:Francais sans sous-titre"  "0:eng:English with music"
        do
            run_cmd "videotool metadata -i \"$file\" -o \"tmp/$file.meta.2.mp4\" --copyright \"$c\" --author \"O.Korach\" --year \"2020\" --default_track 0 --language \"$lang\""
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./*.meta.* tmp/*.meta.* 2>/dev/null
exit 0

