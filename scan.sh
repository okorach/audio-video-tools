#!/bin/bash
#
# media-tools
# Copyright (C) 2019-2020 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
buildDir="build"
[ ! -d $buildDir ] && mkdir $buildDir
pylintReport="$buildDir/pylint-report.out"
banditReport="$buildDir/bandit-report.json"
flake8Report="$buildDir/flake8-report.out"

if [ "$1" != "-nolint" ]; then
  echo "Running pylint"
  rm -f $pylintReport
  pylint *.py */*.py -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" | tee $pylintReport
  re=$?
  if [ "$re" == "32" ]; then
    >&2 echo "ERROR: pylint execution failed, errcode $re, aborting..."
    exit $re
  fi

  echo "Running flake8"
  rm -f $flake8Report
  flake8 --ignore=W503,E128,C901,W504 --max-line-length=150 . >$flake8Report

  echo "Running bandit"
  rm -f $banditReport
  bandit -f json -r . >$banditReport
else
  shift
fi

version=`cat mediatools/version.py | grep MEDIA_TOOLS_VERSION | cut -d "=" -f 2 | cut -d "'" -f 2`

pr_branch=""
for o in $*
do
  key=$(echo $o | cut -d '=' -f 1)
  if [ "$key" == "-Dsonar.pullrequest.key" ]; then
    pr_branch="-Dsonar.pullrequest.branch=foo"
  fi
done

sonar-scanner \
  -Dsonar.projectVersion=$version \
  -Dsonar.python.flake8.reportPaths=$flake8Report \
  -Dsonar.python.pylint.reportPath=$pylintReport \
  -Dsonar.python.bandit.reportPaths=$banditReport \
  $br \
  $*
