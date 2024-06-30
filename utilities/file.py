#
# media-tools
# Copyright (C) 2024 Olivier Korach
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

import os

def rename(old: str, new: str, overwrite: bool = False):
    if os.path.isfile(new):
        if overwrite:
            os.remove(new)
        else:
            file_split = new.split(".")
            base = ".".join(file_split[0:-1])
            ext = file_split[-1]
            seq = 0
            while os.path.isfile(f'{base}.{seq:03}.{ext}'):
                seq += 1
            os.rename(new, f'{base}.bak.{seq:03}.{ext}')
    os.rename(old, new)
