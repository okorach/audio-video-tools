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

rm -r tmp 2>/dev/null

. lib-it.sh

for cmd in it*.sh
do
    if [[ "$cmd" != "$(basename $0)" && "$cmd" != "it-01-image-crop.sh" && "$cmd" != 'it-02-video-crop.sh' ]]; then
        run_cmd "$cmd"
        echo "----------------------------------------"
        echo "SUCCESS: $cmd"
        echo "----------------------------------------"
    fi
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm -r tmp 2>/dev/null
exit 0
