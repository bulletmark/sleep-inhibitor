#!/bin/bash
# Checks if jellyfin server is currently serving media to any user.
# Mark Blakeney, Nov 2020.

TOKEN="$1"
TDIR="$(dirname $0)"

if [[ -f $TDIR/$TOKEN ]]; then
    exit 254
fi

exit 0
