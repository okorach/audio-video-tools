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

let i=0
for f in ./*.jpg
do
    for n in 2 7 11 17 29
    do
        for r in 1% 3% 7% 10 20
        do
            let i=$i+1
            let k=(3*$i+1)%2
            if [[ "$k" == "0" ]]; then
                d=horizontal
            else
                d=vertical
            fi
            let k=(7*$i)%2
            if [[ "$k" == "0" ]]; then
                c=black
            else
                c=white
            fi
            run_cmd "imagetool blinds -i $f -o tmp/$f.blind.$n.$r.jpg -n $n -d $d -c $c -b $r"
        done
    done
done
echo "----------------------------------------"
echo "SUCCESS: $(basename $0)"
echo "----------------------------------------"
rm ./*.blind.* tmp/*.blind.* 2>/dev/null
exit 0
