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

:: Split each PDF file passed as argument into 1 PDF per page (foo.pdf -> foo.page_1.pdf, foo.page_2.pdf, ...)
:: Asks for the quality in ppp: 150 (/ebook, default), 300 (/printer) or 600 (/prepress)

setlocal enabledelayedexpansion
set ppp=150
set /p ppp=Quality in ppp [150, 300, 600] (default 150) ?
for %%F in (%*) do (
    pdftool split -i "%%~F" --ppp !ppp!
)
