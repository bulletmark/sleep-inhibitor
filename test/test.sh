#!/bin/bash
FILE="$(dirname $0)"/"$1"

[[ -f $FILE ]] && exit 254
exit 0
