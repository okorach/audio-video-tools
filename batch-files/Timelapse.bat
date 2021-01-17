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
set /p speed=Speed factor ?:
Rem -an removes audio
for %%F in (%*) do (
    echo E:\Tools\ffmpeg\bin\ffmpeg.exe -i "%%~F" -vf select='not(mod(n,%speed%))',setpts=N/FRAME_RATE/TB -an -vcodec libx264 -b:v 12288k "%%~F.timelapse.mp4"
    E:\Tools\ffmpeg\bin\ffmpeg.exe -i "%%~F" -vf select='not(mod(n,%speed%))',setpts=N/FRAME_RATE/TB -an -vcodec libx264 -b:v 12288k "%%~F.timelapse.mp4"
    rem E:\Tools\ffmpeg\bin\ffmpeg.exe -i %1 -vf framestep=%speed%,setpts=N/FRAME_RATE/TB %1.timelapse.mp4
)
pause


