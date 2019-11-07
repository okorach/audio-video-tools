#!/bin/bash

branchOpt=""
if [ "$1" != "" ]; then
  branchOpt="-Dsonar.branch.name=$1"
fi

key="audio-video-tools"
orgOpt=""
token=$SQ_TOKEN
if [ "$SQ_URL" == "https://sonarcloud.io" ]; then
  key="okorach_audio-video-tools"
  orgOpt="-Dsonar.organization=okorach-github"
  token=$SCLOUD_TOKEN_AV_TOOLS
fi

pylintReport="pylint-report.out"
echo "Running pylint"
rm -f $pylintReport
pylint *.py */*.py -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" | tee $pylintReport
re=$?
if [ "$re" == "32" ]; then
  >&2 echo "ERROR: pylint execution failed, errcode $re, aborting..."
  exit $re
fi

sonar-scanner \
  -Dsonar.projectKey=$key \
  -Dsonar.host.url=$SQ_URL \
  -Dsonar.login=$token \
  -Dsonar.python.pylint.reportPath=$pylintReport
  $orgOpt $branchOpt
