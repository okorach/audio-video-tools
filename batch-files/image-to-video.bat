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

image-to-video -g 5 --framesize 3840x2160 --effect panorama --panorama_effect 0.1,0.9,0.6,0.4 --duration 5 -i "%~1"
image-to-video -g 5 --framesize 3840x2160 --effect zoom --zoom_effect 100,120 -i "%~1"
pause