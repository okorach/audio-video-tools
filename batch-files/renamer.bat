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

:: setlocal enabledelayedexpansion
:: set /p pformat=Photo format XXX - #SEQ# - #TIMESTAMP# - #DEVICE# - #SIZE# ?
:: set /p vformat=Video format XXX - #SEQ# - #TIMESTAMP# - #DEVICE# - #SIZE# - #FPS#fps - #BITRATE#MB ?
:: for %%F in (%*) do (
::    renamer -i "%%~F" -r "%root%"
:: )

:: renamer -r "%root%" -i %* -v DEBUG
set /p prefix=Format (#SEQ# #SIZE# #DEVICE# #TIMESTAMP# #TIME# #FPS# #BITRATE#)?
set /p seqstart=Sequence Start ?
renamer --seqstart %seqstart% --prefix "%prefix%" --photo_format "%prefix%" --video_format "%prefix%" -i %*
