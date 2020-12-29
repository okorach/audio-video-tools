#!/bin/bash

function run_cmd() {
    echo "Running: $*"
	$*
    code=$?
    if [ $code -ne 0 ]; then
        1>&2 echo "========================================"
        1>&2 echo "FAILED: $*"
        1>&2 echo "========================================"
        exit $code
    fi
}
