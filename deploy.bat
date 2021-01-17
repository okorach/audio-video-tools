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
del build/*
del dist/*

python setup.py sdist bdist_wheel

:: Deploy locally for tests
python -m pip uninstall media-tools
for %%a in (dist\*.whl) do (
    echo "y" | python -m pip install %%a
)

:: Deploy on pypi.org once released
if "%1"=="pypi" (
    python -m twine upload dist/*
)