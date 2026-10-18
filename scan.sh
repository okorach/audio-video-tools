#!/bin/bash
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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

dolint=true
tests=pytest
skiptests=0

while [[ $# -ne 0 ]]
do
  case "$1" in
    -nolint)
      dolint=false
      ;;
    -unittest)
      tests=unittest
      ;;
    -skiptests)
      skiptests=1
      ;;
    *)
      scanOpts="$scanOpts $1"
      ;;
  esac
  shift
done

buildDir="build"
owaspDependencyReport="$buildDir/dependency-check-report.json"

[[ ! -d "$buildDir" ]] && mkdir "$buildDir"
rm -rf -- ${buildDir:?"."}/* .coverage */__pycache__ */*.pyc # mediatools/__pycache__  tests/__pycache__

if [[ $skiptests -eq 0 ]]; then
  coverage run -m pytest --junitxml="$buildDir/ut.xml"
  coverage xml -o "$buildDir/coverage.xml"
else
  echo "Skipping tests"
fi

if [[ "$dolint" != "false" ]]; then
  ruff check --output-format=concise . | tee "$buildDir/ruff-report.txt" | python3 ruff2sonar.py >"$buildDir/ruff-report.json"
  pylint *.py */*.py -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" >"$buildDir/pylint-report.out"
  flake8 --ignore=W503,E128,C901,W504,E302,E265,E741,W291,W293,W391,F401,E722 --max-line-length=150 . >"$buildDir/flake8-report.out"
  bandit --exit-zero -f json --skip B311,B303,B101 -r . -x .vscode,./tests >"$buildDir/bandit-report.json"
fi

dependency-check --scan . --format JSON --prettyPrint --out $owaspDependencyReport

version=$(grep MEDIA_TOOLS_VERSION mediatools/version.py | cut -d "=" -f 2 | cut -d "'" -f 2)

pr_branch=""
for o in $scanOpts
do
  key="$(echo $o | cut -d '=' -f 1)"
  if [[ "$key" == "-Dsonar.pullrequest.key" ]]; then
    pr_branch="-Dsonar.pullrequest.branch=foo"
  fi
done


echo "Running: sonar-scanner \
  -Dsonar.projectVersion=$version \
  -Dsonar.dependencyCheck.jsonReportPath=$owaspDependencyReport \
  $pr_branch \
  $scanOpts"

sonar-scanner \
  -Dsonar.projectVersion=$version \
  -Dsonar.dependencyCheck.jsonReportPath=$owaspDependencyReport \
  $pr_branch \
  $scanOpts
