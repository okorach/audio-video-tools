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

res_list="$*"
if [[ "$res_list" == "" ]]; then
    res_list="360x200 720x400 1280x720 1920x1080 3840x2160"
fi

for res in $res_list
do
    run_cmd "videotool slideshow -i *.jpg --resolution $res -o slideshow.$res.mp4"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm ./slideshow.*.mp4 ./slideshow.*.yaml 2>/dev/null
exit 0
