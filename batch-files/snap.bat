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
:: Usage: drop one or more video files or folders onto this batch file.
:: You are asked for a number of photos (evenly spread in each video) or, if left empty, for an interval in seconds.
:: The photos are saved next to each video, named <video name>.1.jpg, <video name>.2.jpg...
::

@echo off

set /p nbr=Number of photos per video (leave empty to snap a photo every N seconds) ?
if "%nbr%"=="" set /p every=Snap a photo every how many seconds ?

if "%nbr%"=="" (
    video-snap -i %* --every %every%
) else (
    video-snap -i %* --nbr_photos %nbr%
)

pause
