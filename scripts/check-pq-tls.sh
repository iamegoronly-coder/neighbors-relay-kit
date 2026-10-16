#!/bin/sh
# Python supplies a portable process timeout (including on macOS).
# Needs Python 3 and OpenSSL 3.5+; publishes no relay events.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/check_pq_tls.py" "$@"
