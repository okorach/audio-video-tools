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

for vb in 2048k 1024k 512k
do
    case $vb in
        "512k")
            ab="32k"
            r="15"
            ;;
        "1024k")
            ab="64k"
            r="30"
            ;;
        *)
            ab="128k"
            r="60"
            ;;
    esac
    run_cmd "videotool profile-encode -i video-1920x1080.mp4 -o tmp/video-1920x1080.encode.$vb.mp4 -r $r --abitrate $ab --vbitrate $vb --width 1280 -o video.encode.$vb.mp4 -p 2mbps"
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm tmp/*.encode.* 2>/dev/null
exit 0
