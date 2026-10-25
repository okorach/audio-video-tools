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

run_cmd "imagetool to-video -i img-3000x4000.jpg -o tmp/img-3000x4000.zoom.1.mp4 --effect zoom --duration 5 --bounds 1,1.3"
run_cmd "imagetool to-video -i img-3000x4000.jpg -o tmp/img-3000x4000.zoom.2.mp4 --effect zoom --duration 3 --bounds 1.2,1.0"
run_cmd "imagetool to-video -i img-3000x4000.jpg -o tmp/img-3000x4000.zoom.3.mp4 --effect zoom -o img-3000x4000.2.zoom.mp4 --effect zoom --duration 7 --bounds 1.1,1.3"
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
rm tmp/*.zoom.* 2>/dev/null
exit 0
