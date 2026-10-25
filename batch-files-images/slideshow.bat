::
:: media-tools
:: Copyright (C) 2019-2026 Olivier Korach
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

set RESOLUTION=
set /p RESOLUTION="Resolution [1920x1080]: "
if "%RESOLUTION%"=="" set RESOLUTION=1920x1080

set FPS=
set /p FPS="Frame rate [50]: "
if "%FPS%"=="" set FPS=50
set QUALITY=
set /p QUALITY="Quality [high, medium, low] (default high): "
if "%QUALITY%"=="" set QUALITY=high

videotool slideshow -i %* --resolution %RESOLUTION% --fps %FPS% --quality %QUALITY%
