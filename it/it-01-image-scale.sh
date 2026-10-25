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

for f in ./*.jpg
do
    for w in "" 128 258 500 800 1024 2000 3000 10000
    do
        for h in "" 64 258 512 800 1024 2000 3000 10000
        do
            if [[ "$f" == "./img-superwide.jpg" && "$h" == "10000" ]]; then
                # Generates a too wide image, skip
                continue
            fi
            run_cmd "imagetool scale -i $f -o tmp/$f.scale.$w.$h.jpg -s ${w}x${h}"
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm tmp/*.scale.* 2>/dev/null
exit 0
