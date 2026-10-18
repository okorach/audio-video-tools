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

:: Encodes the vertical (portrait) files passed as argument in 1080p (1080x1920), with hardware acceleration
:: Asks for the codec (x265 default or x264), the frame rate (default 50fps) and the video bitrate (default 10000k)
:: Each file is replaced by the encoded file, the original is kept as <name>.original.<ext>

setlocal enabledelayedexpansion
set codec=x265
set /p codec=Codec [x265, x264] (default x265) ? 
set fps=50fps
set /p fps=Frame rate [25fps, 30fps, 50fps, 60fps...] (default 50fps) ? 
:: The frame rate can be given with or without the fps suffix: 50 or 50fps
set fps=!fps:fps=!
set bitrate=10000k
set /p bitrate=Video bitrate (default 10000k) ? 

encode -i %* --hw_accel on --vcodec !codec! --width 1080 --height 1920 --vbitrate !bitrate! --acodec aac --abitrate 128k --fps !fps! --keepName

pause
