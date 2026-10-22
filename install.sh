#!/bin/sh
# One-command installation from install.conf: same wizard, same checks, no questions asked.
# Fill in install.conf first, or leave DOMAIN empty and answer the one question. Nothing is downloaded or executed from the network
# by this wrapper; extra options are passed to setup.sh and take precedence over the file.
set -eu
KIT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$KIT/setup.sh" --config "$KIT/install.conf" --yes "$@"
