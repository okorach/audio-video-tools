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
:: Usage: drop one or more video files or folders onto this batch file.
:: Each file is color-enhanced in place (original renamed to .original.<ext>).
:: Applies the eq color filter (saturation/contrast/brightness/gamma) with CPU encoding by default.
:: Pass --gpu_filters to use GPU hw acceleration instead (eq filter is then skipped).
::

@echo off

:loop
if "%~1"=="" goto end
video-enhance -i "%~1"
shift
goto loop

:end
pause
