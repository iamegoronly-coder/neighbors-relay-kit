#!/bin/sh
# Local, inspectable entry point. No downloaded code is executed by this wrapper.
set -eu
KIT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$KIT/scripts/setup-relay.py" "$@"
