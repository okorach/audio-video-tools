::
:: media-tools
:: Copyright (C) 2019-2021 Olivier Korach
:: mailto:olivier.korach AT gmail DOT com
::
:: This program is free software; you can redistribute it and/or
:: modify it under the terms of the GNU Lesser General Public
:: License as published by the Free Software Foundation; either
:: version 3 of the License, or (at your option) any later version.
::
:: This program is distributed in the hope that it will be useful,
:: but WITHOUT ANY WARRANTY; without even the implied warranty of
:: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
:: Lesser General Public License for more details.
::
:: You should have received a copy of the GNU Lesser General Public License
:: along with this program; if not, write to the Free Software Foundation,
:: Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
::

setlocal enabledelayedexpansion

set vcodec=h265
set vbitrate=12000k
set acodec=aac
set abitrate=128k
set width=1920
set hwaccel=on

set /p "width=Video width [%width%] ? "
set /p "vbitrate=Video bitrate [%vbitrate%] ? "
set /p "vcodec=Video codec [%vcodec%] ? "
set /p "hwaccel=Hardware acceleration [%hwaccel%] ? "
set /p "fps=FPS ? "

encode -i %* --hw_accel "%hwaccel%" --width "%width%" --vbitrate "%vbitrate%" --vcodec "%vcodec%" --acodec "%acodec%" --abitrate "%abitrate%" --fps "%fps%"

pause