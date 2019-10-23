#!/bin/bash

branch=""
if [ "$1" != "" ]; then
  branch="-Dsonar.branch.name=$1"
fi

sonar-scanner \
  -Dsonar.projectKey=okorach_audio-video-tools \
  -Dsonar.organization=okorach-github \
  -Dsonar.sources=. \
  -Dsonar.host.url=https://sonarcloud.io \
  -Dsonar.login=$SCLOUD_TOKEN_AV_TOOLS \
  $branch
