#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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


class FileTypeError(Exception):
    '''Error when passing a non media file'''
    def __init__(self, file="file", expected_type='media', message=None):
        self.file = file
        self.message = message
        if message is None:
            self.message = "File {} is not of the expected {} type".format(file, expected_type)
        super().__init__(self.message)


class InputError(Exception):
    '''Error when passing wrong input arguments for media transformation'''
    def __init__(self, message=None, operation=None):
        self.message = message
        self.operation = operation
        if message is None:
            self.message = "Input parameters error"
        if operation is not None:
            self.message = "{}: {}".format(operation, self.message)
        super().__init__(self.message)


class DimensionError(Exception):
    '''Error when copputing image or video dimensions'''
    def __init__(self, message=None, operation=None):
        self.message = message
        self.operation = operation
        if message is None:
            self.message = "Dimensions error"
        if operation is not None:
            self.message = "{}: {}".format(operation, self.message)
        super().__init__(self.message)
